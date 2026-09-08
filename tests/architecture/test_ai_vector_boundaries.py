"""Guards for the standalone AI-01 application boundaries."""

import ast
from pathlib import Path


def test_ai_application_keeps_storage_imports_in_adapter() -> None:
    for path in Path("src/greader/ai/app").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                if path.name == "service.py":
                    assert all(
                        alias.name != "InMemoryVectorRepository" for alias in node.names
                    ), path
            else:
                continue
            for module in modules:
                assert not module.startswith(
                    (
                        "sqlalchemy",
                        "sqlmodel",
                        "psycopg",
                        "pgvector",
                        "greader.database",
                    )
                ), (path, module)
                if path.name != "main.py":
                    assert not module.startswith("greader.ai.database"), path


def test_ai_application_has_only_synchronous_functions() -> None:
    for directory in ("app", "database"):
        for path in Path(f"src/greader/ai/{directory}").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            assert not any(
                isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree)
            )
