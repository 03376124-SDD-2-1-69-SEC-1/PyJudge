"""Architecture guards for module ownership."""

import ast
import importlib
from pathlib import Path

CORE_ROOT = Path("src/greader/core")

# Generation is intentionally a pure proxy: its route forwards the request to the
# GenerationClient port and returns the response unchanged. With no business logic,
# retries, response mapping, or error translation, a service layer would add no value.
ROUTE_SERVICE_EXCEPTIONS = {"generation"}


def test_core_never_imports_ai() -> None:
    for source_file in CORE_ROOT.rglob("*.py"):
        assert "greader.ai" not in source_file.read_text(), source_file


def test_routes_do_not_call_repository_ports_directly() -> None:
    for source_file in CORE_ROOT.glob("*/routes.py"):
        if source_file.parent.name in ROUTE_SERVICE_EXCEPTIONS:
            continue

        tree = ast.parse(source_file.read_text())
        repository_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.endswith(".repository")
        ]
        assert not repository_imports, source_file


def test_assignment_placeholders_are_importable() -> None:
    for module in ("models", "schemas", "repository", "service", "routes"):
        importlib.import_module(f"greader.core.assignments.{module}")
