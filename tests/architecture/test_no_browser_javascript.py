"""Architecture guard for project-authored HTML."""

import re
from pathlib import Path

TEMPLATE_ROOT = Path("src/greader/web/templates")
FORBIDDEN = re.compile(r"<script\b|javascript:|\son[a-z]+\s*=", re.IGNORECASE)


def test_project_templates_do_not_contain_browser_javascript() -> None:
    templates = list(TEMPLATE_ROOT.rglob("*.html"))

    assert templates, "expected project-authored templates"
    for template in templates:
        assert FORBIDDEN.search(template.read_text()) is None, template
