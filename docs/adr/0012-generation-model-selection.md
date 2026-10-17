---
status: accepted
date: 2026-10-17
task: OPS-26
---

# The generation models on A-01 come from a measured free-tier comparison

## Context

ADR-0009 made OpenRouter the only provider and left the model open. The
default has been `poolside/laguna-s-2.1:free` since then, chosen ad hoc, and
`GENERATION_MODEL_ALLOWLIST` still falls back to just that one model, so
A-01 has nothing else an Admin may switch to. OPS-25 (structured output
with `response_format`) also waits for this choice, because each model
supports it differently.

OpenRouter's free tier changes weekly. In October 2026 the account can see
sixteen `:free` models, several of which look plausible for Thai problem
drafts, so the pick was measured, not guessed.

## Method

`scripts/compare_generation_models.py` (this branch, rerunnable) does the
comparison. It reuses `OpenRouterGenerationClient`'s `_SYSTEM_PROMPT` and
`_parse_response`, so every draft has to survive exactly the parsing
production does, and every `expected_output` is computed the way the app
computes it (PR #46): the draft's `reference_solution` is executed locally
against each input the draft itself produced (5 s per case, the same
contract the CodeRunner fills in production).

Three seed statements from `scripts/seed/pith-100-manifest.csv` are the
inputs, all Thai with no extraction defects (the registry rejects Private-
Use-Area glyphs and broken ำ; PyMuPDF found none in these three):

- `0029` กบ (frog), loops, easy
- `1073` มด (mravi), simulation, easy
- `1083` ลงทุนซื้อหุ้น (stock), arrays, medium

### Candidates

Six `:free` models, picked from OpenRouter's current list as the cheap
families most likely to draft Thai: the incumbent
`poolside/laguna-s-2.1:free` and its sibling `laguna-xs-2.1:free`,
`google/gemma-4-31b-it:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`,
`nvidia/nemotron-3-super-120b-a12b:free` and
`thinkingmachines/inkling:free`.

### Judge

The statement quality of each draft (thai_fluency, clarity_correctness,
originality_not_copied, usable, Thai note) is scored by the LLM judge the
team's reviewer round uses, sent verbatim with the source statement and the
candidate filled into it. `google/gemini-3.8-flash` was tried first and
the project key cannot pay for it (Forbidden), likewise
`thinkingmachines/inkling-small:free` and
`nvidia/nemotron-3-lightning:free` (Forbidden/BadRequest), so the judge on
this run was `google/gemma-4-26b-a4b-it:free`. It is a sibling of the
candidate `gemma-4-31b` — a residual bias to keep in mind; both were smoke
tested for parse compliance before the run.

Each (candidate × task) raw reply is kept on this machine under
`data/model-comp/` (git-ignored), one `.raw` file per reply, and judge
rows land in `results.json` next to them.

## Result

One row per (model × task), the summary printed by the script at
`data/model-comp/results.json` after the run of 2026-10-17:

| model | parse | solution runs | thai | clarity | originality | usable |
|---|---|---|---|---|---|---|
| poolside/laguna-s-2.1:free | 3/3 | 10/10 | 3.0 (empty once) | 4.0 | 2.67 | 0/3 |
| poolside/laguna-xs-2.1:free | 2/3 | 5/5 | 2.0 | 3.0 | 1.5 | 0/3 |
| google/gemma-4-31b-it:free | 0/3 | — | — | — | — | 0/3 (gateway down) |
| nvidia/nemotron-3-ultra-550b-a55b:free | 1/3 | 5/5 | 3.0 | 3.0 | 1.0 | 0/3 (2 calls dead) |
| nvidia/nemotron-3-super-120b-a12b:free | 2/3 | 3/7 | 5.0 | 3.5 | 1.0 | 0/3 |
| thinkingmachines/inkling:free | 0/3 | — | — | — | — | 0/3 (key forbidden) |

What the per-task rows add, quoting the judge's Thai notes:

- **laguna-s** (the incumbent) is the only candidate that parsed all three
  and whose reference solution ran clean on all ten of its own inputs.
  Its weaknesses: on `1073` it answered in English (thai_fluency empty),
  and the `1083` draft left a stray Japanese fragment «すべて» — a failure
  mode the draft stage cannot catch and only the statement review round
  would.
- **laguna-xs** drafts Thai full of wrong-letter typos ("ด้วนช้า"
  instead of "ด้วยช้า", "เต็นบรรทัด"), and its `1083` reply was broken
  JSON the production parser rejects.
- **nemotron-3-super** writes the most natural Thai of the set (thai 5.0
  on both drafts it completed) but recopies the source statement almost
  word for word (originality 1.0), and its `1083` solution passed 0 of 4
  of its own test inputs — the expected outputs would all be blanks for
  the Instructor to fill at T-04. It also broke JSON on `0029`.
- **nemotron-3-ultra** replied to one call in three; the other two died
  as `ResponseValidationError` before any draft existed.
- **gemma-4-31b** hit gateway errors on all three calls during this run,
  so it remains unmeasured rather than measured-bad.
- **inkling** is forbidden under this project key.

(No draft was judged `usable`; the rubric is deliberately strict — every
candidate failed either on missing examples, on leftover fragments, or on
recopying the source. For Questly's own flow this is less damaging than
it reads: drafting from a source statement that stays close on the
scenario is the normal case, which is why originality is reported but not
driving this decision.)

## Decision

- `GENERATION_MODEL` / `DEFAULT_GENERATION_MODEL` stays
  **`poolside/laguna-s-2.1:free`** — the only candidate with a clean
  format-and-solve record, and production-proven since OPS-23.
- `GENERATION_MODEL_ALLOWLIST` / `DEFAULT_GENERATION_ALLOWLIST` becomes
  the three measured models an Admin may pick on A-01:
  `poolside/laguna-s-2.1:free`, `poolside/laguna-xs-2.1:free`,
  `nvidia/nemotron-3-super-120b-a12b:free`. Unset `GENERATION_MODEL`
  plus an unset allowlist resolves to that triple; a custom
  `GENERATION_MODEL` outside it stands alone as before.
- Excluded on evidence, not taste: `nemotron-3-ultra` (two-thirds of its
  calls die), `gemma-4-31b` (gateway unreachable from this account —
  re-measure if wanted), `inkling` (forbidden for this key), everything
  paid (ADR-0009 keeps generation).
- No schema change: the model rides per generation call, which A-01
  already reads from `Settings`.

## Consequences

- OPS-25 can start: structured-output support is verified per model in
  its tests, and the allowlist it must deal with is exactly these three
  `:free` slugs.
- The free tier changes weekly; this comparison is a snapshot, and
  OpenRouter may retire any of these slugs. Re-run
  `scripts/compare_generation_models.py` before touching the allowlist
  again, and expect a re-run to re-judge the same three seed statements.
- `nemotron-3-super` on the allowlist means an Instructor can pick a
  model whose `expected_output` fills blank on hard problems; T-04
  already treats blanks as "fill it yourself", so the failure is visible
  in the UI, not silent.
- The judge picked (`gemma-4-26b`) shares a family with one candidate;
  a re-run should try upgrading the judge to a paid model first (account
  credits permitting), then fall back to this one so scores stay
  comparable to this ADR.
- `.env.example` ships the allowlist as a real value now, not empty, so
  a fresh environment gets the measured set without reading this ADR.
