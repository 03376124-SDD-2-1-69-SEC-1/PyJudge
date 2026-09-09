# Repository-assigned int ids for Assignment and TestCase

GReader runs on a single node with one Postgres database, so a client-generated
UUID buys nothing — no offline writes, no multi-master merge, nothing a
`BIGSERIAL` can't do more cheaply. `core/topics` generates `str(uuid4())` in
the service layer because it predates this decision and was built as the
demo reference slice, not because UUIDs are the house style; `AGENTS.md`
already calls that out ("In-memory Topics still uses UUID; that is the demo,
not the pattern to copy for persisted tables"). Assignment and TestCase
instead use the pattern the locked schema commits to: `id` is `int | None`
on the domain dataclass, `None` meaning only "not yet persisted," and
`AssignmentRepository.create()` is the sole operation allowed to turn that
`None` into a real id — every other Protocol method takes and returns an
entity that already has one. The service never invents an id; it builds the
entity, calls `create`, and uses the object `create` returns from that point
on, exactly as `InMemoryAssignmentRepository` does today with a counter and
as the CORE-10 SQL adapter will do by letting Postgres assign the
`BIGSERIAL`. Consequence: the SQL adapter owns the id sequence, not the
domain layer, which keeps database concerns out of `core/`; and
`tests/unit/core/assignments/test_repository_contract.py` is the
enforcement — it is a parametrized suite any `AssignmentRepository`
implementation must pass, so CORE-10 registers the SQL adapter alongside
`InMemoryAssignmentRepository` and inherits every check without rewriting
them. Reversing this decision means changing the Protocol's `create`
signature and every adapter that implements it, not swapping out one
adapter in isolation.
