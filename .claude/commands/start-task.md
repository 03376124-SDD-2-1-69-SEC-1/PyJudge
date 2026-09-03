---
description: Pick one of my assigned tasks, branch for it, then interview me before any code is written.
argument-hint: [owner name, e.g. พาย]
---

Owner for this session: $1

Do not write or edit application code during this command. Stop after the plan.

## Step 1 — Preconditions

Run `git status --porcelain` and `git branch --show-current`.

- If the working tree is dirty: stop. Show what is uncommitted and let them
  deal with it. Do not stash, commit, or discard anything.
- If `$1` is empty: ask whose tasks to list. Do not guess from git config.

## Step 2 — Offer only their tasks

Read `docs/task-scope.md`. Take every row whose Owner column contains `$1`,
including shared rows like `นัด + โปรแกรม`.

Run `git branch -a` and drop any task whose branch already exists locally or on
the remote — that work has started.

Show what is left as a numbered list: TASK-ID, the done condition, and the
paths it may touch. If nothing is left, say so and stop.

Ask which one. Wait. Accept only a number or a TASK-ID from that list — if they
name a task belonging to someone else, say who owns it and stop.

## Step 3 — Branch

Confirm the type prefix with them (`feat`, `fix`, `chore`, `docs`, `refactor`),
propose a slug from the task title, and show the full branch name for approval.

Once approved:

```
git switch dev
git pull
git switch -c <type>/<TASK-ID>-<slug>
```

If `git pull` fails or `dev` is behind, stop and report — do not branch from a
stale `dev`.

## Step 4 — Interview

Now follow `.claude/commands/grill-me.md` from its Step 2 onward, using the task
selected above. Do not repeat its Step 1; the task is already known.

Its push-back rules apply in full. Being the tech lead is not an exemption —
if this task needs a schema change, an alembic run, or a contract edit, say so
out loud and make it an explicit decision rather than a quiet one.

## Step 5 — Stop

Emit the plan block from `grill-me.md` Step 4, then wait. Do not start
implementing until told to.
