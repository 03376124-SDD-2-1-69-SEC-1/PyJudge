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


def test_core_never_imports_an_orm_or_storage_client() -> None:
    """`core/` sees a Protocol and a dataclass, never SQLModel or boto3."""
    forbidden = ("sqlmodel", "sqlalchemy", "boto3", "botocore", "greader.database")
    violations = []
    for source_file in sorted(CORE_ROOT.rglob("*.py")):
        text = source_file.read_text()
        violations.extend(
            f"{source_file}: {name}" for name in forbidden if name in text
        )

    assert not violations, (
        "core/ must not import an ORM or a storage client (AGENTS.md "
        "'Layering'). Violations:\n" + "\n".join(violations)
    )


def test_routes_do_not_call_repository_ports_directly() -> None:
    for source_file in CORE_ROOT.glob("*/routes.py"):
        if source_file.parent.name in ROUTE_SERVICE_EXCEPTIONS:
            continue

        tree = ast.parse(source_file.read_text())
        port_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.endswith(".ports")
        ]
        assert not port_imports, source_file


def test_every_slice_module_is_importable() -> None:
    slices = {
        "topics": ("models", "schemas", "ports", "service", "routes"),
        "assignments": (
            "models",
            "schemas",
            "ports",
            "service",
            "routes",
            "testcase_routes",
        ),
        "uploads": ("models", "schemas", "ports", "service", "routes"),
        "generation": ("schemas", "ports", "routes"),
    }
    for slice_name, modules in slices.items():
        for module in modules:
            importlib.import_module(f"greader.core.{slice_name}.{module}")
