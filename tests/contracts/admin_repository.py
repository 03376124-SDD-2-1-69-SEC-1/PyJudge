from dataclasses import replace

from questly.core.admin.ports import AdminRepository


class AdminRepositoryContractTests:
    """Contract tests for AdminRepository implementations (Fake & SQL)."""

    def test_update_replaces_every_field_and_get_reads_it_back(
        self, repo: AdminRepository
    ) -> None:
        current = repo.get_ai_settings()
        changed = replace(
            current,
            model=f"{current.model}-changed",
            daily_quota=current.daily_quota + 1,
            max_pages=current.max_pages + 1,
            require_citations=not current.require_citations,
        )

        saved = repo.update_ai_settings(changed)

        assert saved == changed
        assert repo.get_ai_settings() == changed
