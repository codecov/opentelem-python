import json

import pytest
import responses
from coverage import Coverage
from coverage.xmlreport import XmlReporter

from codecovopentelem import CoverageExporter


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


def test_export_span(mocker, mocked_responses):
    mocker.patch.object(
        XmlReporter,
        "report",
        side_effect=lambda a, outfile: outfile.write("somedatahere"),
    )
    cov = Coverage()
    cov_storage, repository_token, profiling_identifier, codecov_endpoint = (
        mocker.MagicMock(pop_cov_for_span=mocker.MagicMock(return_value=cov)),
        "repository_token",
        "identifier",
        "http://codecov.test/endpoint",
    )
    mocked_responses.add(
        responses.POST,
        "http://codecov.test/profiling/uploads",
        json={"raw_upload_location": "http://storage.test/endpoint"},
        status=200,
        content_type="application/json",
    )
    mocked_responses.add(
        responses.PUT,
        "http://storage.test/endpoint",
        status=200,
        content_type="application/json",
    )
    exporter = CoverageExporter(
        cov_storage, repository_token, profiling_identifier, codecov_endpoint, 1
    )
    span = mocker.MagicMock(to_json=mocker.MagicMock(return_value="{}"))
    assert exporter.export([span])
    assert len(mocked_responses.calls) == 2
    assert (
        mocked_responses.calls[0].request.url == "http://codecov.test/profiling/uploads"
    )
    print(mocked_responses.calls[1].request.body)
    assert json.loads(mocked_responses.calls[1].request.body) == {
        "spans": [{"codecov": {"type": "bytes", "coverage": "c29tZWRhdGFoZXJl"}}],
        "untracked": [],
    }
