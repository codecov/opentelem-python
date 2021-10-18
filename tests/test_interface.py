from uuid import uuid4

import pytest
import responses

from codecovopentelem import (
    CodecovCoverageGenerator,
    CoverageExporter,
    UnableToStartProcessorException,
    get_codecov_opentelemetry_instances,
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
            code=None,
        )
    assert exc.value.args == ("Codecov profiling needs a code set",)


def test_get_codecov_opentelemetry_instances_with_call_made(mocker, mocked_responses):
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
                    "version_identifier": "version_identifier",
                    "environment": "production",
                    "code": "code",
                }
            )
        ],
    )
    res = get_codecov_opentelemetry_instances(
        repository_token="repository_token",
        sample_rate=0.1,
        untracked_export_rate=0.1,
        code="code",
        version_identifier="version_identifier",
        environment="production",
    )
    assert len(res) == 2
    generator, exporter = res
    assert isinstance(generator, CodecovCoverageGenerator)
    assert isinstance(exporter, CoverageExporter)


def test_get_codecov_opentelemetry_instances_with_call_not_made(
    mocker, mocked_responses
):
    res = get_codecov_opentelemetry_instances(
        repository_token="repository_token",
        sample_rate=0.1,
        untracked_export_rate=0.1,
        code="code",
        version_identifier="version_identifier",
        environment="production",
        needs_version_creation=False,
    )
    assert len(res) == 2
    generator, exporter = res
    assert isinstance(generator, CodecovCoverageGenerator)
    assert isinstance(exporter, CoverageExporter)
