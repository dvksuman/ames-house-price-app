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
