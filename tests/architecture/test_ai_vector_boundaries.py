"""Guards for AI-01 domain boundaries and persisted contract alignment."""

import ast
import re
from importlib.util import resolve_name
from pathlib import Path

from sqlalchemy import CheckConstraint

from greader.ai.app.models import EMBEDDING_DIMENSION
from greader.ai.app.service import SOURCE_STATUSES
from greader.database.rag.tables import EMBEDDING_DIM, KnowledgeSource


def test_ai_application_keeps_storage_imports_in_adapter() -> None:
    for path in Path("src/greader/ai").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    package = ".".join(path.parent.relative_to("src").parts)
                    module = resolve_name("." * node.level + module, package)
                modules = [module, *(f"{module}.{alias.name}" for alias in node.names)]
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


def test_ai_application_has_only_synchronous_functions() -> None:
    paths = [
        *Path("src/greader/ai").rglob("*.py"),
        Path("src/greader/database/rag/vector_repository.py"),
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(
            isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree)
        )


def test_embedding_dimension_matches_existing_table() -> None:
    assert EMBEDDING_DIMENSION == EMBEDDING_DIM


def test_source_statuses_match_existing_check_constraint() -> None:
    constraints = [
        constraint
        for constraint in KnowledgeSource.__table_args__
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_knowledge_sources_status"
    ]
    assert len(constraints) == 1
    allowed_statuses = frozenset(re.findall(r"'([^']+)'", str(constraints[0].sqltext)))
    assert allowed_statuses == SOURCE_STATUSES
