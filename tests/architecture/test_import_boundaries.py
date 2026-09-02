"""Architecture guards for module ownership."""

import importlib
from pathlib import Path

CORE_ROOT = Path("src/greader/core")


def test_core_never_imports_ai() -> None:
    for source_file in CORE_ROOT.rglob("*.py"):
        assert "greader.ai" not in source_file.read_text(), source_file


def test_assignment_placeholders_are_importable() -> None:
    for module in ("models", "schemas", "repository", "service", "routes"):
        importlib.import_module(f"greader.core.assignments.{module}")
