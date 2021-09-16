import json
import logging
import random
import re
import urllib.parse
from base64 import b64encode
from decimal import Decimal
from io import StringIO
from typing import Optional, Tuple

import coverage
import requests
from coverage.xmlreport import XmlReporter
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

log = logging.getLogger("codecovopentelem")


class CodecovCoverageStorageManager(object):
    def __init__(self, writeable_folder: str):
        if writeable_folder is None:
            writeable_folder = "/home/codecov"
        self._writeable_folder = writeable_folder
        self.inner = {}

    def start_cov_for_span(self, span_id):
        cov = coverage.Coverage(data_file=f"{self._writeable_folder}/.{span_id}file")
        self.inner[span_id] = cov
        cov.start()

    def stop_cov_for_span(self, span_id):
        cov = self.inner.get(span_id)
        if cov is not None:
            cov.stop()

    def pop_cov_for_span(self, span_id):
        return self.inner.pop(span_id, None)


class CodecovCoverageGenerator(SpanProcessor):
    def __init__(
        self,
        cov_storage: CodecovCoverageStorageManager,
        sample_rate: Decimal,
        name_regex: re.Pattern = None,
    ):
        self._cov_storage = cov_storage
        self._sample_rate = sample_rate
        self._name_regex = name_regex

    def _should_profile_span(self, span, parent_context):
        return random.random() < self._sample_rate and (
            self._name_regex is None or self._name_regex.match(span.name)
        )

    def on_start(self, span, parent_context=None):
        if self._should_profile_span(span, parent_context):
            span_id = span.context.span_id
            self._cov_storage.start_cov_for_span(span_id)

    def on_end(self, span):
        span_id = span.context.span_id
        self._cov_storage.stop_cov_for_span(span_id)


class CoverageExporter(SpanExporter):
    def __init__(
        self,
        cov_storage: CodecovCoverageStorageManager,
        repository_token: str,
        profiling_identifier: str,
        codecov_endpoint: str,
    ):
        self._cov_storage = cov_storage
        self._repository_token = repository_token
        self._profiling_identifier = profiling_identifier
        self._codecov_endpoint = codecov_endpoint

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
        data = []
        untracked_spans = []
        for span in spans:
            span_id = span.context.span_id
            cov = self._cov_storage.pop_cov_for_span(span_id)
            s = json.loads(span.to_json())
            if cov is not None:
                s["codecov"] = self._load_codecov_dict(span, cov)
                data.append(s)
            else:
                untracked_spans.append(s)
        url = urllib.parse.urljoin(self._codecov_endpoint, "/profiling/uploads")
        res = requests.post(
            url,
            headers={"Authorization": f"repotoken {self._repository_token}"},
            json={"profiling": self._profiling_identifier},
        )
        try:
            res.raise_for_status()
        except requests.HTTPError:
            log.warning("Unable to send profiling data to codecov")
            return SpanExportResult.FAILURE
        location = res.json()["raw_upload_location"]
        requests.put(
            location,
            headers={"Content-Type": "application/txt"},
            data=json.dumps({"spans": data, "untracked": untracked_spans}).encode(),
        )
        return SpanExportResult.SUCCESS


def get_codecov_opentelemetry_instances(
    repository_token: str,
    profiling_identifier: str,
    sample_rate: float,
    name_regex: Optional[re.Pattern],
    codecov_endpoint: str = None,
    writeable_folder: str = None,
) -> Tuple[CodecovCoverageGenerator, CoverageExporter]:
    """
    Entrypoint for getting a span processor/span exporter
        pair for getting profiling data into codecov

    Args:
        repository_token (str): The profiling-capable authentication token
        profiling_identifier (str): The identifier for what profiling one is doing
        sample_rate (float): The sampling rate for codecov
        name_regex (Optional[re.Pattern]): A regex to filter which spans should be
            sampled
        codecov_endpoint (str, optional): For configuring the endpoint in case
            the user is in enterprise (not supported yet). Default is "https://api.codecov.io/"
        writeable_folder (str, optional): A folder that is guaranteed to be write-able
            in the system. It's only used for temporary files, and nothing is expected
            to live very long in there.
    """
    if codecov_endpoint is None:
        codecov_endpoint = "https://api.codecov.io"
    manager = CodecovCoverageStorageManager(writeable_folder)
    generator = CodecovCoverageGenerator(manager, sample_rate, name_regex)
    exporter = CoverageExporter(
        manager, repository_token, profiling_identifier, codecov_endpoint
    )
    return (generator, exporter)
