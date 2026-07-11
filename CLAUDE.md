# Project Rule: Everything Goes Through OpenSpec

This project uses OpenSpec (`spec-driven` schema) for all planning and implementation.
See `openspec/config.yaml` for tech stack and project context.

## The rule

No source code (anything under `src/`, `Dockerfile*`, `docker-compose.yml`,
`requirements.txt`, etc.) is written or edited except to implement a task that is
`[ ]` or `[~]` (in progress) in an active change's `openspec/changes/<name>/tasks.md`.

If a request doesn't already correspond to a task:
1. Check if it fits an existing open change — if so, add the task to that change's
   `tasks.md` (and its `specs/` if it implies new/changed behavior) before writing code.
2. If it doesn't fit any open change, it needs its own `/opsx:propose` first.

Ad hoc code changes "just to fix something quickly" are not allowed, even for
small things — add or update a task first, then implement it.

## Why

Keeps the specs in `openspec/changes/*/specs/` the actual source of truth for what
the system does, instead of code drifting away from documented intent. This matters
for a graded assignment where the specs/tasks are the evidence trail of what was
built and why.

## Working style

**HARD GATE — explore before every new group:**
Before implementing any new task group, ALWAYS run `/opsx:explore` to think through
best practices, design decisions, tradeoffs, and non-obvious pitfalls for that group.
Do NOT write any code until the explore session is complete and the user says to proceed.
Skipping this step is not allowed, even if the task seems straightforward.

Implement one `tasks.md` group at a time, not the whole file in one pass. After each
group, explain the key concepts/decisions in the generated code before moving to the
next group (the user is optimizing for learning, not just a working app).

## Design decisions — automatic updates

Whenever the user clarifies, answers a question, or makes a design choice during
any session (e.g. "use 0 not median", "keep encoding in Group 4", "save as CSV"),
record it immediately in `openspec/changes/build-house-price-app/design.md` under
the relevant group's section. Do not wait for the user to ask.

Include: the decision itself, the rationale/reason the user gave (or the reasoning
behind the recommended option they accepted), and any implications for other groups.

## Lessons Learned — automatic updates

Whenever a non-trivial problem is encountered and resolved (an error diagnosed,
a workaround applied, a non-obvious tool or library choice made, an external
service limitation discovered), append a new entry to `LESSONS_LEARNED.md`
**immediately** — same session, before moving to the next task. Do not wait
for the user to ask.

Entry format: LL-NN title, When, What happened, Why it happened, Fix, Takeaway.

This rule exists so the document grows organically as problems are found, not
as a summary exercise at the end when details are forgotten.

## Task completion checklist — MANDATORY before moving to next task

After every task is done, complete ALL of the following steps in order before
starting the next task. Do not skip any step, even if it seems unnecessary.

1. **Run the code** — execute the script and confirm it produces real output
2. **Verify outputs** — check files were created, row counts are right, nulls are gone, etc.
3. **Mark `[x]` in tasks.md** — update the task checkbox immediately
4. **Update LESSONS_LEARNED.md** — append any non-trivial problem that was hit and fixed
5. **Update TOI.md** — append any new useful command used during the task
6. **Update design.md** — record any design decision or clarification made during the task
7. **Git commit** — create a checkpoint commit before moving to the next group

## Session checkpoint — suggested at group boundaries

After completing each group (and before starting the next), create a checkpoint file:

```
SESSION_YYYY-MM-DD_<topic>.md  (in project root)
```

Include: tasks completed, last git commit hash, key output files + shapes, any bugs fixed,
and the exact next step (group + task numbers). This file is the handoff brief for the next
session — read it first, skip re-deriving state from git log or conversation history.

**When to create:** After every group commit, or any time context is approaching compression
(long session, many tool calls). If the session ends without a checkpoint, the next session
starts cold.

**This is a suggestion, not a hard gate** — but skipping it means the next session wastes
time re-establishing state that could have been written in 2 minutes.

**Reminder rule:** At the end of any group commit, or when the user says they want to stop,
Claude must say:
> "To continue next time: `/clear` or open a new session, then paste:
> 'Read `SESSION_YYYY-MM-DD_<topic>.md` and continue with Group N. Run `/opsx:explore` first.'"

## Integration verification — mandatory before starting a new group

Before implementing any new task group that consumes outputs from a previous group,
run all preceding scripts in sequence and verify the full file-handoff chain works:

1. **Run the chain** — execute each script in order (ingest → preprocess → eda → …)
2. **Check exit codes** — every script must exit cleanly with no exceptions
3. **Verify output files exist** — confirm each expected file was written to the correct path
4. **Check row/column counts** — ensure the dataset shape is correct at each stage
5. **Spot-check for nulls** — verify no unexpected NaN values crept in through the handoff

Do NOT start a new group until this check passes. If any step fails, fix the integration
bug first, commit the fix, then proceed.

This rule exists because pipeline bugs caught early (before Prefect schedules them every
2 minutes, or before Docker Compose runs them at startup) cost 30 seconds to fix.
Caught late, they cost hours of debugging across multiple services.

## No cheating, no shortcuts, always ask when in doubt

- **No cheating**: Never fake, mock, hardcode, or fabricate data, outputs, or results.
  Every number, file, and metric must come from actually running the code.
- **No shortcuts**: Do not skip steps, bypass validation, or cut corners to make
  something "just work." If a task is hard, understand why and fix it properly.
- **Always ask when in doubt**: If the requirement is unclear, the right approach is
  uncertain, or two options seem equally valid — STOP and ask the user before proceeding.
  A wrong assumption wastes more time than a clarifying question.

## Code comments — mandatory

Every line of source code written or edited in this project must have a plain English
comment directly above it (or on the same line for very short lines) explaining what
that line does in simple, non-technical terms. Write as if the reader has never seen
Python before.

This applies to: imports, constants, function definitions, every statement inside
functions, and the `if __name__ == "__main__"` block. No line goes without a comment.

## TOI — automatic updates

Whenever a useful command is used during the session (git, curl, python, pip,
openspec, docker, or any CLI tool) that the user may want to reference later,
append it to `TOI.md` under the appropriate section. Do not wait for the user
to ask. If no section fits, add a new one.

This covers any command that: solved a problem, revealed useful diagnostic
information, or is non-obvious enough that the user would benefit from having
it written down.
