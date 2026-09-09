"""Executable versions of the rules in AGENTS.md and docs/task-scope.md.

Each test here exists because a prose rule was broken by someone who never saw it.
When you add a rule to AGENTS.md, add its test here in the same PR.
"""

import ast
from pathlib import Path

CORE_ROOT = Path("src/greader/core")
SRC_ROOT = Path("src/greader")
MAIN_PY = Path("src/greader/main.py")
TESTS_ROOT = Path("tests")
LEGACY_ASSIGNMENTS_TEST_DIR = TESTS_ROOT / "unit" / "core" / "topics" / "assignments"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def _is_pytest_filename(path: Path) -> bool:
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def test_no_any_under_core() -> None:
    violations = []
    for source_file in sorted(CORE_ROOT.rglob("*.py")):
        tree = _parse(source_file)
        for node in ast.walk(tree):
            is_any_name = isinstance(node, ast.Name) and node.id == "Any"
            is_any_import = (
                isinstance(node, ast.ImportFrom)
                and node.module == "typing"
                and any(alias.name == "Any" for alias in node.names)
            )
            if is_any_name or is_any_import:
                violations.append(f"{source_file}:{node.lineno}")

    assert not violations, (
        "`Any` is banned under core/ (AGENTS.md 'Typing rules' -> 'No Any'). "
        "Replace it with a concrete type or a domain dataclass. Violations:\n"
        + "\n".join(violations)
    )


def _is_bare_dict_annotation(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id in ("dict", "Dict")
    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name):
            return value.id in ("dict", "Dict")
        if isinstance(value, ast.Attribute):
            return value.attr in ("dict", "Dict")
    return False


def test_service_and_route_functions_do_not_return_bare_dict() -> None:
    violations = []
    for filename in ("service.py", "routes.py"):
        for source_file in sorted(CORE_ROOT.glob(f"*/{filename}")):
            tree = _parse(source_file)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.returns is not None
                    and _is_bare_dict_annotation(node.returns)
                ):
                    violations.append(f"{source_file}:{node.lineno}: {node.name}")

    assert not violations, (
        "A service or route must return a domain object, not a dict "
        "(AGENTS.md 'Typing rules' -> 'No Any': 'A service or repository must "
        "never return a bare dict from a public method'). Violations:\n"
        + "\n".join(violations)
    )


def test_no_pytest_files_under_src() -> None:
    matches = sorted(p for p in SRC_ROOT.rglob("*.py") if _is_pytest_filename(p))

    assert not matches, (
        "Test files belong under tests/, not src/greader/. Move these:\n"
        + "\n".join(str(p) for p in matches)
    )


def test_pytest_filename_check_ignores_the_test_cases_slice_name() -> None:
    """`core/test_cases/` is a domain slice (Assignment test cases), not a
    tests directory. The src-test-file check above matches filenames, not
    directory names, so it must not flag `test_cases/models.py`."""
    assert not _is_pytest_filename(Path("src/greader/core/test_cases/models.py"))
    assert _is_pytest_filename(Path("src/greader/core/test_cases/test_foo.py"))
    assert _is_pytest_filename(Path("src/greader/core/test_cases/foo_test.py"))


def _is_include_router_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
    )


def test_routers_are_mounted_only_inside_create_app() -> None:
    tree = _parse(MAIN_PY)
    create_app_node = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "create_app"
        ),
        None,
    )
    assert create_app_node is not None, f"{MAIN_PY} must define create_app()"

    inside_create_app = {id(node) for node in ast.walk(create_app_node)}

    violations = [
        f"{MAIN_PY}:{node.lineno}"
        for node in ast.walk(tree)
        if _is_include_router_call(node) and id(node) not in inside_create_app
    ]

    assert not violations, (
        "include_router(...) must be called only inside create_app() -- a "
        "module-scope call after `app = create_app()` skips the per-test "
        "create_app() fixture and mounts the router on the shared singleton "
        "only. Violations:\n" + "\n".join(violations)
    )


def test_no_files_under_legacy_assignments_test_path() -> None:
    matches = (
        sorted(LEGACY_ASSIGNMENTS_TEST_DIR.rglob("*.py"))
        if LEGACY_ASSIGNMENTS_TEST_DIR.exists()
        else []
    )

    assert not matches, (
        "tests/unit/core/topics/assignments/ nests Assignment tests under the "
        "Topics slice by accident. Move HTTP tests to tests/integration/ and "
        "unit tests to tests/unit/core/assignments/. Found:\n"
        + "\n".join(str(p) for p in matches)
    )


def _imports_http_test_client(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name in ("AsyncClient", "TestClient") for alias in node.names)
        for node in ast.walk(tree)
    )


# A field goes in either allowlist only when a use case reads it and the PR
# says which one. Expected first entry for ALLOWED_TIMESTAMP_FIELDS:
# `approved_at` on a draft, once GReader's approval flow needs it -- unlike
# `created_at`/`updated_at`, that's a business fact, not row bookkeeping.
ALLOWED_TIMESTAMP_FIELDS: set[str] = set()  # empty on purpose
ALLOWED_ID_SUFFIX_FIELDS = {"artifact_id"}


def _dataclass_field_names(tree: ast.Module) -> list[tuple[str, str, int]]:
    fields = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append((node.name, item.target.id, item.lineno))
    return fields


def test_domain_models_hold_no_table_only_fields() -> None:
    violations = []
    for source_file in sorted(CORE_ROOT.glob("*/models.py")):
        tree = _parse(source_file)
        for class_name, field_name, lineno in _dataclass_field_names(tree):
            if (
                field_name.endswith("_at")
                and field_name not in ALLOWED_TIMESTAMP_FIELDS
            ):
                violations.append(
                    f"{source_file}:{lineno}: {class_name}.{field_name} "
                    "(looks like a persistence timestamp)"
                )
            elif (
                field_name.endswith("_id")
                and field_name not in ALLOWED_ID_SUFFIX_FIELDS
            ):
                violations.append(
                    f"{source_file}:{lineno}: {class_name}.{field_name} "
                    "(looks like a foreign-key column)"
                )

    assert not violations, (
        "AGENTS.md 'Layering' -> models.py: the domain layer holds business "
        "concepts only and does not carry fields that exist to satisfy a "
        "table (see CORE-11). A field ending in `_at` or `_id` must be "
        "allowlisted in ALLOWED_TIMESTAMP_FIELDS / ALLOWED_ID_SUFFIX_FIELDS "
        "if a use case reads it -- say which one in the PR. Violations:\n"
        + "\n".join(violations)
    )


def test_http_client_tests_live_under_integration() -> None:
    violations = []
    for source_file in sorted(TESTS_ROOT.rglob("*.py")):
        if TESTS_ROOT / "integration" in source_file.parents:
            continue
        if _imports_http_test_client(_parse(source_file)):
            violations.append(str(source_file))

    assert not violations, (
        "Files that use AsyncClient or TestClient are HTTP tests and belong "
        "under tests/integration/, matching "
        "tests/integration/test_topics_api.py. Violations:\n" + "\n".join(violations)
    )
