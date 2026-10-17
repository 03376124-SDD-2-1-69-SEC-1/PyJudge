"""run_case sandboxes model-written code: no secrets in, no repo cwd.

The child runs `python -I` with a PATH-only env and a fresh temporary cwd;
these tests prove both guarantees without touching the network. They
monkeypatch the real environment's OPENROUTER_API_KEY to make sure the
--env-file-loaded key never reaches the model's stdout.
"""

import pytest
import scripts.compare_generation_models as comparison
from scripts.compare_generation_models import ROOT, run_case


def _probe(exits_on_secret: str = "3", exits_on_repo: str = "4") -> str:
    """Code that exits 0 only when both sandbox guarantees hold."""
    return "\n".join(
        (
            "import os, sys",
            f"repo = {str(ROOT)!r}",
            f"if os.environ.get('OPENROUTER_API_KEY'): sys.exit({exits_on_secret})",
            f"if os.getcwd() == repo: sys.exit({exits_on_repo})",
            "sys.exit(0)",
        )
    )


def test_child_process_cannot_see_the_api_key_and_cannot_run_in_the_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parent exposes the key and sits in the repo; the child still exits 0."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "loaded-by---env-file")
    assert run_case(_probe(), stdin="")


def test_exit_code_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """True on exit 0, False on any other exit or on the timeout."""
    monkeypatch.setattr(comparison, "SOLUTION_RUN_TIMEOUT", 2)
    assert run_case("import sys; sys.exit(0)", stdin="")
    assert not run_case("import sys; sys.exit(2)", stdin="")
    # the 5 s production default is patched away, so this one is the timeout
    assert not run_case("while True: pass", stdin="")


def test_child_env_is_path_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second secret beyond the API key never reaches the child either."""
    monkeypatch.setenv("QUESTLY_REVIEW_SECRET", "also-not-for-the-child")
    probe = (
        "import os, sys\n"
        "if os.environ.get('QUESTLY_REVIEW_SECRET'): sys.exit(3)\n"
        "sys.exit(0)\n"
    )
    assert run_case(probe, stdin="")
