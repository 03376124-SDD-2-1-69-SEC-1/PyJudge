---
status: accepted
date: 2026-10-12
task: CORE-20
---

# Generate runs as a background job, with a progress page

## Context

ADR-0007 section 11 listed "Submit and Generate are synchronous: no progress
display and no Cancel (S-02a, T-03c)" as a deliberate gap. A generation takes
tens of seconds: one model call with a 60 s timeout and up to 15 s of retries,
then the reference solution run once per Test Case. The browser showed nothing
until it ended, and the free OpenRouter quota an Instructor could spend was not
visible anywhere.

## Decision

This supersedes the "no progress display" and "no Cancel" bullets of ADR-0007
section 11 **for Generate only**. Submit stays synchronous (S-02a is still
waiting on CORE-17).

`POST /classes/{id}/generate` validates the form, checks both quotas, registers
a `GenerationJob` and answers 303 to `/classes/{id}/generate/jobs/{job_id}`.
The work runs in a FastAPI `BackgroundTasks` function, which is synchronous and
so runs in the thread pool. T-03c re-requests itself with
`<meta http-equiv="refresh" content="2">` and lists the steps the job really
went through (`GenerationStep`). A done job answers 303 to the Draft; a failed
or stale one renders T-03d with the form refilled.

`GenerationClient.generate(request, on_step)` reports each stage as it starts.
`RETRIEVING` exists in `GenerationStep` but no page shows it until retrieval
(AI-05) is wired into generation.

T-03 also shows the provider's own free quota, read through a new
`ProviderQuota` port: `OpenRouterProviderQuota` reads
`free_model_daily_requests` from the key metadata, caches it for 30 seconds and
drops the cache after a generation succeeds. For a model that does not end in
`:free` OpenRouter reports nothing, so the snapshot is `unknown` and says how
many generations succeeded today. OpenRouter's per-minute limit is not reported
and is not invented.

### Jobs live in this process

Jobs are kept by `InMemoryGenerationJobStore` in `integrations/`, behind the
`GenerationJobStore` port. The PoC has one user and one process, and a job only
matters for as long as someone is watching it. Limits, accepted:

- A restart loses every job. T-03c then says "This generation is no longer
  available, try again". Nothing was saved and no quota was charged for work
  that did not finish; ids start at the clock so an old link never lands on a
  different job.
- A second worker cannot see the first one's jobs. Running more than one
  `uvicorn` worker needs a database store first.
- Nothing evicts a finished job, so the dict grows by one small entry per
  Generate until the process restarts.
- `create_unless_running` and `update(job_id, change)` are each one atomic
  step: two clicks on Generate make one job, and a cancel cannot be overwritten
  by the thread's next step. A database store can implement both with a unique
  partial index and `SELECT ... FOR UPDATE`, and no caller changes.

The architecture test that forbids `InMemory*` classes in `src/` keeps an
explicit allowlist; this class is its only entry.

### Cancel and stale jobs mean "stop waiting"

T-03c's wireframe has a Cancel button. Python cannot stop a thread in the
middle of a model call, and OpenRouter keeps counting a request it has
accepted, so Cancel marks the job `cancelled` and returns the Instructor to
T-03 with the form refilled. The same holds for a running job older than three
minutes, which reads as failed.

The thread notices at its next step: `on_step` raises
`GenerationAbandonedError` for a job that is no longer running, so the run
stops before the Draft is saved and before the daily Quota is charged. What it
cannot take back is the model call already made. A result that arrives after
the job was cancelled or went stale is thrown away.

## Consequences

- `GenerationClient` gained a required `on_step` argument. The three adapters
  (`OpenRouterGenerationClient`, `StubGenerationClient`,
  `FakeGenerationClient`) report their real stages; `GenerationService.generate`
  defaults it to a no-op so the JSON API, which stays synchronous, is unchanged.
- There is a small window between the last `on_step(SAVING)` check and the
  job being marked done. A cancel landing inside it still saves the Draft and
  charges the Quota; the Draft shows up under Drafts.
- `GenerationService` takes a `GenerationJobStore` and a `ProviderQuota`, and
  every use case on jobs takes the Actor first. Only the Instructor who started
  a job can read it: another Instructor or a non-member gets 404, a Student
  member 403.
