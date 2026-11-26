"""OpenAPI metadata: descriptions, tags and documented error responses."""

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

DESCRIPTION = """
Records software packages and their releases, and reports each package's
latest version by semantic version order, so `1.10.0` ranks above `1.9.0`.

Every error is returned as `application/problem+json`, following
[RFC 9457](https://www.rfc-editor.org/rfc/rfc9457). Branch on `type`, not on
the text of `detail`.
"""

TAGS = [
    {"name": "packages", "description": "Register packages and look them up."},
    {"name": "releases", "description": "Add releases to a package and look them up."},
    {"name": "health", "description": "Liveness check for load balancers and probes."},
]


class Problem(BaseModel):
    """An error, in RFC 9457 problem details format."""

    type: str = Field()
    title: str = Field()
    status: int = Field()
    detail: str = Field()
    instance: str = Field()


class ValidationProblem(Problem):

    errors: list[dict[str, str]] = Field(
        examples=[[{"field": "name", "message": "String should match pattern '^[a-z][a-z0-9-]*$'"}]]
    )


def problem(description: str, schema: str = "Problem") -> dict:
    return {
        "description": description,
        "content": {
            "application/problem+json": {
                "schema": {"$ref": f"#/components/schemas/{schema}"}
            }
        },
    }


INVALID = {422: problem("The request body is invalid.", "ValidationProblem")}


UNAVAILABLE = {
    503: problem(
        "The database is unreachable or too slow. Retry after the number of "
        "seconds in the `Retry-After` header."
    )
}


def operation_id_from_name(route: APIRoute) -> str:
    return route.name


def add_problem_schemas(app: FastAPI) -> None:
    original_openapi = app.openapi

    def openapi() -> dict: 
        if app.openapi_schema:
            return app.openapi_schema
        spec = original_openapi()
        schemas = spec.setdefault("components", {}).setdefault("schemas", {})
        for model in (Problem, ValidationProblem):
            schemas[model.__name__] = model.model_json_schema()

        # FastAPI documents its own 422 shape on every endpoint with parameters.
        # Our handler replaces that shape. Endpoints with a body get ours;
        # endpoints with only string path parameters can never return 422.
        for path in spec["paths"].values():
            for operation in path.values():
                if "422" not in operation["responses"]:
                    continue
                if "requestBody" in operation:
                    operation["responses"]["422"] = INVALID[422]
                else:
                    del operation["responses"]["422"]
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)

        app.openapi_schema = spec
        return spec

    app.openapi = openapi