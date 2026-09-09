"""The maintainer's regression test for the PUT-wipes-fields bug.

Reported twice, on PR #14 and PR #15: `update_assignment_as_dict` builds a
fresh `Assignment` from the request payload alone and hands it to
`repository.update()`, so fields the payload did not send -- `test_cases`,
`artifact_id` -- get reset to their dataclass defaults instead of staying
untouched. See AGENTS.md "Typing rules" -> "Partial updates must not drop
fields".

This test is owned by the maintainer, not by whoever ships the fix, so it
cannot go green by narrowing itself around the bug. It is expected to fail
on `dev` today -- the Assignments slice is still a placeholder there, so
these requests 404 -- and must fail the same way against PR #14 and PR #15
as they stand, and pass only once the service loads the existing entity and
merges.

Note: `AssignmentCreate` has no `artifact_id` field -- that column is set by
the generation flow, not by CRUD -- so this test cannot drive a non-null
`artifact_id` through the public HTTP contract alone. It instead asserts
that whatever value was there before the update (None, on a freshly created
assignment) is still there after -- which is enough to catch the payload
clobbering the field.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import create_app


@pytest.fixture()
async def client():
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.xfail(
    reason="Assignments CRUD (CORE-04) not merged to dev yet -- flips to an "
    "unexpected pass, and this must be un-xfailed, the moment it lands with "
    "the merge-on-update fix.",
    strict=True,
)
@pytest.mark.anyio
async def test_title_only_update_preserves_test_cases_and_artifact_id(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/assignments",
        json={
            "title": "Original title",
            "problem_statement": "Do X",
            "difficulty": "easy",
            "metadata": {},
        },
    )
    assert created.status_code == 201
    assignment = created.json()
    assignment_id = assignment["id"]

    tc_created = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json={
            "input_data": "1 2",
            "expected_output": "3",
            "is_hidden": False,
            "order_index": 1,
        },
    )
    assert tc_created.status_code == 201

    updated = await client.put(
        f"/api/v1/assignments/{assignment_id}",
        json={"title": "New title"},
    )
    assert updated.status_code == 200
    body = updated.json()

    assert body["title"] == "New title"
    assert body["problem_statement"] == assignment["problem_statement"]
    assert body["difficulty"] == assignment["difficulty"]
    assert body["artifact_id"] == assignment["artifact_id"]

    test_cases = (
        await client.get(f"/api/v1/assignments/{assignment_id}/test-cases")
    ).json()
    assert len(test_cases) == 1, (
        "PUT with a title-only payload must not drop test_cases -- the "
        "service must load the existing Assignment and merge, not build a "
        "fresh one from the payload alone."
    )
