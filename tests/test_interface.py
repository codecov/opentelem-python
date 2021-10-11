import json
from uuid import uuid4

import pytest
import responses
from coverage import Coverage
from coverage.xmlreport import XmlReporter

from codecovopentelem import (
    CodecovCoverageGenerator,
    CoverageExporter,
    get_codecov_opentelemetry_instances,
    UnableToStartProcessorException,
)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


def test_get_codecov_opentelemetry_instances_nothing_set(mocker, mocked_responses):
    with pytest.raises(UnableToStartProcessorException) as exc:
        get_codecov_opentelemetry_instances(
            repository_token="repository_token",
            sample_rate=0.1,
            untracked_export_rate=0.1,
        )
    assert exc.value.args == (
        "Codecov profiling needs either the id or identifier + environment",
    )


def test_get_codecov_opentelemetry_instances_nothing_set_env_and_version(
    mocker, mocked_responses
):
    uuid = uuid4().hex
    mocked_responses.add(
        responses.POST,
        "https://api.codecov.io/profiling/versions",
        json={"external_id": uuid},
        status=200,
        content_type="application/json",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "version_identifier": "profiling_identifier",
                    "environment": "production",
                }
            )
        ],
    )
    res = get_codecov_opentelemetry_instances(
        repository_token="repository_token",
        sample_rate=0.1,
        untracked_export_rate=0.1,
        profiling_identifier="profiling_identifier",
        environment="production",
    )
    assert len(res) == 2
    generator, exporter = res
    assert isinstance(generator, CodecovCoverageGenerator)
    assert isinstance(exporter, CoverageExporter)
