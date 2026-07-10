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

Implement one `tasks.md` group at a time, not the whole file in one pass. After each
group, explain the key concepts/decisions in the generated code before moving to the
next group (the user is optimizing for learning, not just a working app).

## Lessons Learned — automatic updates

Whenever a non-trivial problem is encountered and resolved (an error diagnosed,
a workaround applied, a non-obvious tool or library choice made, an external
service limitation discovered), append a new entry to `LESSONS_LEARNED.md`
**immediately** — same session, before moving to the next task. Do not wait
for the user to ask.

Entry format: LL-NN title, When, What happened, Why it happened, Fix, Takeaway.

This rule exists so the document grows organically as problems are found, not
as a summary exercise at the end when details are forgotten.

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
