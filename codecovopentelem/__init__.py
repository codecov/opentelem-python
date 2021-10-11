import json
import logging
import random
import urllib.parse
from base64 import b64encode
from decimal import Decimal
from enum import Enum
from io import StringIO
from typing import Dict, Optional, Pattern, Tuple

import coverage
import requests
from coverage.xmlreport import XmlReporter
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

log = logging.getLogger("codecovopentelem")


class CoverageSpanFilter(Enum):
    regex_name_filter = "name_regex"
    span_kind_filter = "span_kind"


class UnableToStartProcessorException(Exception):
    pass


class CodecovCoverageStorageManager(object):
    def __init__(self, writeable_folder: str, filters: Dict):
        if writeable_folder is None:
            writeable_folder = "/home/codecov"
        self._writeable_folder = writeable_folder
        self.inner = {}
        self._filters = filters

    def possibly_start_cov_for_span(self, span) -> bool:
        span_id = span.context.span_id
        if self._filters.get(
            CoverageSpanFilter.regex_name_filter
        ) and not self._filters.get(CoverageSpanFilter.regex_name_filter).match(
            span.name
        ):
            return False
        if self._filters.get(
            CoverageSpanFilter.span_kind_filter
        ) and span.kind not in self._filters.get(CoverageSpanFilter.span_kind_filter):
            return False
        cov = coverage.Coverage(data_file=f"{self._writeable_folder}/.{span_id}file")
        self.inner[span_id] = cov
        cov.start()
        return True

    def stop_cov_for_span(self, span):
        span_id = span.context.span_id
        cov = self.inner.get(span_id)
        if cov is not None:
            cov.stop()

    def pop_cov_for_span(self, span):
        span_id = span.context.span_id
        return self.inner.pop(span_id, None)


class CodecovCoverageGenerator(SpanProcessor):
    def __init__(
        self, cov_storage: CodecovCoverageStorageManager, sample_rate: Decimal,
    ):
        self._cov_storage = cov_storage
        self._sample_rate = sample_rate

    def _should_profile_span(self, span, parent_context):
        return random.random() < self._sample_rate

    def on_start(self, span, parent_context=None):
        if self._should_profile_span(span, parent_context):
            self._cov_storage.possibly_start_cov_for_span(span)

    def on_end(self, span):
        self._cov_storage.stop_cov_for_span(span)


class CoverageExporter(SpanExporter):
    def __init__(
        self,
        cov_storage: CodecovCoverageStorageManager,
        repository_token: str,
        profiling_id: str,
        codecov_endpoint: str,
        untracked_export_rate: float,
    ):
        self._cov_storage = cov_storage
        self._repository_token = repository_token
        self._profiling_id = profiling_id
        self._codecov_endpoint = codecov_endpoint
        self._untracked_export_rate = untracked_export_rate

    def _load_codecov_dict(self, span, cov):
        k = StringIO()
        coverage_dict = {}
        try:
            reporter = XmlReporter(cov)
            reporter.report(None, outfile=k)
            k.seek(0)
            d = k.read().encode()
            coverage_dict["type"] = "bytes"
            coverage_dict["coverage"] = b64encode(d).decode()
        except coverage.CoverageException:
            pass
        return coverage_dict

    def export(self, spans):
        tracked_spans = []
        untracked_spans = []
        for span in spans:
            cov = self._cov_storage.pop_cov_for_span(span)
            s = json.loads(span.to_json())
            if cov is not None:
                s["codecov"] = self._load_codecov_dict(span, cov)
                tracked_spans.append(s)
            else:
                if random.random() < self._untracked_export_rate:
                    untracked_spans.append(s)
        if not tracked_spans and not untracked_spans:
            return SpanExportResult.SUCCESS
        url = urllib.parse.urljoin(self._codecov_endpoint, "/profiling/uploads")
        try:
            res = requests.post(
                url,
                headers={"Authorization": f"repotoken {self._repository_token}"},
                json={"profiling": self._profiling_id},
            )
            res.raise_for_status()
        except requests.RequestException:
            log.warning("Unable to send profiling data to codecov")
            return SpanExportResult.FAILURE
        location = res.json()["raw_upload_location"]
        requests.put(
            location,
            headers={"Content-Type": "application/txt"},
            data=json.dumps(
                {"spans": tracked_spans, "untracked": untracked_spans}
            ).encode(),
        )
        return SpanExportResult.SUCCESS


def get_codecov_opentelemetry_instances(
    repository_token: str,
    sample_rate: float,
    untracked_export_rate: float,
    filters: Optional[Dict] = None,
    profiling_identifier: Optional[str] = None,
    environment: Optional[str] = None,
    profiling_id: Optional[str] = None,
    codecov_endpoint: str = None,
    writeable_folder: str = None,
) -> Tuple[CodecovCoverageGenerator, CoverageExporter]:
    """
    Entrypoint for getting a span processor/span exporter
        pair for getting profiling data into codecov

    Notice that either `profiling_id` or `profiling_identifier` and `environment` need to be set.
        If `profiling_id` is set, we just use it directly on the exporter. If not, we will use
        `profiling_identifier` and `environment` to generate fetch a `profiling_id` from the
        database

    Args:
        repository_token (str): The profiling-capable authentication token
        sample_rate (float): The sampling rate for codecov
        untracked_export_rate (float): Description
        filters (Optional[Dict], optional): A dictionary of filters for determining which
            spans should have its coverage tracked
        profiling_identifier (Optional[str], optional): The identifier for what profiling one is doing
        environment (Optional[str], optional): Which environment this profiling is running on
        profiling_id (Optional[str], optional): Description
        codecov_endpoint (str, optional): For configuring the endpoint in case
            the user is in enterprise (not supported yet). Default is "https://api.codecov.io/"
        writeable_folder (str, optional): A folder that is guaranteed to be write-able
            in the system. It's only used for temporary files, and nothing is expected
            to live very long in there.
    """
    codecov_endpoint = codecov_endpoint or "https://api.codecov.io"
    if profiling_id is None:
        if profiling_identifier is None or environment is None:
            raise UnableToStartProcessorException(
                "Codecov profiling needs either the id or identifier + environment"
            )
        response = requests.post(
            urllib.parse.urljoin(codecov_endpoint, "/profiling/versions"),
            json={
                "version_identifier": profiling_identifier,
                "environment": environment,
            },
            headers={"Authorization": f"repotoken {repository_token}"},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise UnableToStartProcessorException()
        profiling_id = response.json()["external_id"]
    manager = CodecovCoverageStorageManager(writeable_folder, filters or {})
    generator = CodecovCoverageGenerator(manager, sample_rate)
    exporter = CoverageExporter(
        manager,
        repository_token,
        profiling_id,
        codecov_endpoint,
        untracked_export_rate,
    )
    return (generator, exporter)
