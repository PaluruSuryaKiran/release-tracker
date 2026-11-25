"""Print the service's OpenAPI spec as JSON.

Run from services/package-service:

    python -m package_service.export_openapi > openapi.json
"""

import json

from package_service.main import app


def render_spec() -> str:
    """The spec as stable, reviewable JSON: sorted keys, indented, newline at the end."""
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    print(render_spec(), end="")