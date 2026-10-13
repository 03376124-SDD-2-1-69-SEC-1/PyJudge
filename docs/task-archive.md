# Task archive

Rows moved out of `docs/task-scope.md` because they no longer apply. Nothing
here is offered by `/start-task`. Rows are kept, not deleted, so the reason a
task disappeared can still be found.

Archived 2026-09-25 (task `chore/task-scope-cleanup`).

| TASK-ID | Owner | Archived | Reason | Original row |
|---|---|---|---|---|
| CORE-07 | นัด + โปรแกรม | 2026-09-25 | Superseded by ADR-0007: publishing a Draft is CORE-15 (`POST /api/v1/drafts/{id}/publish`), its page is FE-08. Row had been closed since ADR-0007. | May touch `core/assignments/`, `web/templates/`, `core/assignments/routes.py`; done when: closed, superseded by ADR-0007 |
| FE-02 | โปรแกรม | 2026-09-25 | Superseded by ADR-0007: the T-03 generate page is part of FE-08. `web/templates/generate.html` does not exist. | May touch `web/templates/generate.html`, `core/generation/routes.py` |
| FE-03 | โปรแกรม | 2026-09-25 | Superseded by ADR-0007: the T-04 review stepper is part of FE-08. `web/templates/review.html` does not exist. | May touch `web/templates/review.html`, `core/assignments/routes.py` |
| FE-04 | โปรแกรม | 2026-09-25 | Superseded by ADR-0007: T-04 steps 3–4 are part of FE-08. `web/templates/save.html` does not exist. | May touch `web/templates/save.html`, `core/assignments/routes.py` |

Archived 2026-10-13 (task `docs/OPS-27-sync-task-scope`).

| TASK-ID | Owner | Archived | Reason | Original row |
|---|---|---|---|---|
| UI-01 | พาย | 2026-10-13 | Superseded by UI-02: the design source moved from Figma GradeFlow to Figma Make, and `docs/ui-audit.md` was created under UI-02 (commit `8e91b3b`) instead. | Status open; May touch `web/templates/`; creates: `docs/ui-audit.md`; done when: compare the Figma GradeFlow mocks with the templates in `web/templates/` in a table in `docs/ui-audit.md` (page, template, Figma frame, result: match / mismatch / no mock), then split the mismatches into sub-tasks for the team |
