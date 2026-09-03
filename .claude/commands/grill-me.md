---
description: Interview me about my current task before writing any code, and hold me to the project's agreed constraints.
---

You are about to interview the developer about the task they are starting.
Do not write or edit any code during this command. Produce a plan and stop.

## Step 1 — Work out who this is

Run `git branch --show-current`. Extract the TASK-ID from the branch name
(`<type>/<TASK-ID>-<slug>`).

Read `docs/task-scope.md` and find the row for that TASK-ID.

- If the branch has no TASK-ID, or the ID is not in the table: say so and ask
  which task this is. Do not guess.
- If the branch is `main` or `dev`: stop. Tell them to branch from `dev` first.

State back in one line: the task, its owner, the paths it may touch, and its
done condition. Then continue.

## Step 2 — Ask, one question at a time

Ask no more than five questions total. Wait for each answer before asking the
next. Do not ask anything already answered by `CLAUDE.md` or the code.

Cover whichever of these are actually unclear for this task:

- What is the smallest version of this that satisfies the done condition?
- Which existing file is the closest thing to what you are building, and are
  you following it?
- What is the input and the output at the boundary — the HTTP shape, or the
  function signature?
- What happens on the error paths? Missing record, duplicate, empty input,
  bad reference.
- What will the test assert, and at which seam — service or HTTP?

If an answer is vague ("handle errors properly", "the usual CRUD", "same as
topics but for assignments"), do not accept it. Ask again for the specific
case. Vague answers here become wrong code later.

## Step 3 — Push back where it is warranted

Push back if any of these are true. Name the rule, say why it exists, and
offer the version that fits.

| What they said | Why it fails |
|---|---|
| anything `async` | this project is sync end to end |
| `Depends()` for the service | services come off `request.app.state` |
| needs a new column, table, or index | schema is locked; that is an OPS task for พาย |
| needs to run alembic | the database is shared; a downgrade destroys other people's work |
| SQL or business rules in a route | routes map HTTP to a service call and nothing else |
| an ORM import under `core/` | adapters live in `database/core/` only |
| `core/` importing `ai/` | the dependency only runs one way |
| a change to the `/v1/generations` contract | it is shared with the other repo; that is a conversation, not a commit |
| files outside the row in `task-scope.md` | say which files and ask them to confirm before including them |
| "I'll add tests later" | the done condition includes them |
| a UUID primary key on a persisted table | keys are BIGSERIAL; the in-memory Topics demo is not the pattern |

Push back once, clearly, with the alternative. If they have a reason and
overrule you, note it in the plan and move on — you are a check, not a gate.

Do not push back on style, naming, or anything not on this list.

## Step 4 — Write the plan

Output, and nothing else:

```
TASK      <id> — <title>
OWNER     <name>
SCOPE     <files this will touch>
BUILD     <3-6 numbered steps>
TESTS     <what is asserted, at which seam>
OPEN      <anything still undecided, or "none">
FLAGGED   <what you pushed back on and how it was resolved, or "none">
```

Then stop and wait. Do not start implementing until they tell you to.
