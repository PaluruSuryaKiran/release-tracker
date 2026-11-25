from pathlib import Path

from package_service.export_openapi import render_spec
from package_service.main import app


def test_spec_has_title_version_and_license():
    info = app.openapi()["info"]
    assert info["title"] == "release-tracker"
    assert info["version"]
    assert info["license"]["identifier"] == "Apache-2.0"


def test_operation_ids_are_handler_names():
    spec = app.openapi()
    ids = {
        operation["operationId"]
        for path in spec["paths"].values()
        for operation in path.values()
    }
    assert ids == {
        "health_check",
        "create_package",
        "get_package",
        "create_release",
        "get_release",
    }


def test_every_endpoint_has_a_summary_and_tag():
    for path in app.openapi()["paths"].values():
        for operation in path.values():
            assert operation.get("summary")
            assert operation.get("tags")


def test_errors_are_documented_as_problem_json():
    spec = app.openapi()
    responses = spec["paths"]["/v1/packages"]["post"]["responses"]
    assert set(responses) >= {"201", "409", "422"}
    assert "application/problem+json" in responses["409"]["content"]
    assert "application/json" not in responses["422"]["content"]
    assert {"Problem", "ValidationProblem"} <= spec["components"]["schemas"].keys()


def test_422_is_documented_only_where_a_body_is_sent():
    spec = app.openapi()
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    for path in spec["paths"].values():
        for operation in path.values():
            has_body = "requestBody" in operation
            assert ("422" in operation["responses"]) == has_body
            if has_body:
                assert list(operation["responses"]["422"]["content"]) == [
                    "application/problem+json"
                ]


def test_committed_spec_is_up_to_date():
    committed = Path(__file__).parent.parent / "openapi.json"
    assert committed.read_text() == render_spec(), (
        "openapi.json is out of date. Regenerate it with:\n"
        "    python -m package_service.export_openapi > openapi.json"
    )