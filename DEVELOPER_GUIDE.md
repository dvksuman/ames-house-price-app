# Project Guide — How Everything Works

This guide is for anyone who wants to:
- Run this app from scratch on their own machine
- Understand what the OpenSpec files are and how to read them
- Understand what the SESSION files are
- Understand the Claude hooks that enforce deterministic behaviour during development

---

## 1. Running the App From Scratch

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git installed
- That's it — no Python, no pip, no MLflow install needed locally

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/dvksuman/ames-house-price-app.git
cd ames-house-price-app

# 2. Start all 5 services
docker compose up
```

Wait ~30 seconds for all health checks to pass. You'll see log lines like:
```
api-1          | INFO: Application startup complete.
api-streamlit-1| Started server process
api-mlflow-1   | Listening at: http://0.0.0.0:5000
```

### What's available

| UI | URL | What it is |
|----|-----|-----------|
| Streamlit Dashboard | http://localhost:8501 | Main user-facing app |
| FastAPI Swagger Docs | http://localhost:8000/docs | Interactive API explorer |
| MLflow UI | http://localhost:5000 | Model training runs + registry |
| Prefect UI | http://localhost:4200 | Scheduled pipeline + run history |

### Using the dashboard (http://localhost:8501)

The Streamlit app has three views — switch between them using the radio buttons at the top:

**EDA** — Exploratory Data Analysis. Shows the SalePrice distribution, correlation heatmap,
and a scatter plot of the top feature vs SalePrice. All charts were generated during
the data pipeline and are served via the FastAPI backend.

**Predict Price** — Enter house features (overall quality, living area, garage cars, etc.)
and click Predict. The FastAPI `/predict` endpoint loads the registered XGBoost model
from MLflow and returns a predicted sale price in dollars.

**App Details** — Live status of all backend services: health check, registered model
info from MLflow, experiment metrics for all three models, Prefect deployment info,
and the last 10 pipeline run records.

### Stopping

```bash
docker compose down        # removes containers (clean stop)
# or
docker compose stop        # pauses containers (faster restart)
docker compose start       # resume after stop
```

### Restarting after a stop

```bash
docker compose up          # no --build needed unless you changed code
```

---

## 2. The OpenSpec Files

OpenSpec is a spec-driven development system. The idea: before writing any code,
you write a proposal, a design, and a task list. The code is only allowed to change
if a task is marked in-progress in that task list. This creates a paper trail of
exactly what was built and why.

### Where they live

```
openspec/
  changes/
    archive/
      2026-07-11-build-house-price-app/   ← the completed change (archived)
        proposal.md     ← what we decided to build and why
        design.md       ← all design decisions made during the build
        tasks.md        ← the 60-task checklist (59/60 complete)
        specs/          ← capability specs (what each part of the system does)
  specs/                ← live specs updated when the change was archived
    api-access/
    data-pipeline/
    ml-pipeline/
    prediction-dashboard/
```

### Reading the files

**`proposal.md`** — Start here. It explains the problem, what was built, and the
scope of the change. Written before any code, updated if scope changed.

**`design.md`** — The decision log. Every time a non-obvious choice was made during
development ("use absolute path mount for mlruns", "model type param is ridge/lasso/xgboost
not the registry name"), it was recorded here immediately with the reasoning.
This is the most useful file for understanding *why* the code looks the way it does.

**`tasks.md`** — The 60-task checklist, organized into 11 groups (scaffolding, ingestion,
preprocessing, EDA, DataOps, ML, MLflow, API, Dashboard, Docker, E2E verification).
Each `[x]` means the task was implemented, run, and verified. `[ ]` means it was
intentionally left for manual steps (e.g. screenshots).

**`specs/`** — Capability specs. Each spec describes what a capability does from a
behaviour perspective (not implementation). Think of them as living documentation
for what the system is supposed to do, updated when the change was archived.

### Why archive?

When a change is complete, `openspec archive` moves it from `changes/` to
`changes/archive/` and updates the live `specs/` directory. This signals the build
is done and keeps the active changes list clean for the next piece of work.

---

## 3. The SESSION Files

### The problem they solve

This project was built across multiple work sessions over several days. Claude Code
has a context window — it can only "remember" a certain amount of conversation before
older messages are compressed or lost. When a session ends and a new one begins,
Claude starts completely fresh. It has no memory of:

- Which tasks were finished
- What was verified working
- What bugs were fixed and how
- What the next step is

Without a handoff document, every new session wastes 10–15 minutes re-deriving this
state — re-reading git log, re-checking which files exist, re-running health checks
just to figure out where to start.

SESSION files solve this by writing down everything that matters, in one place,
at the moment it's freshest — right after the session's final commit.

---

### What a SESSION file contains

A SESSION file is a structured snapshot of exactly where the project stands. It has:

**1. Date and last commit hash**
So you can instantly locate the exact state in git if you need to go back.

**2. A group-by-group status table**
Every task group listed with its status — complete, in-progress, or not started.
You don't need to open tasks.md to get the overview.

**3. What was verified working**
Not just "it was built" but "it was run and checked." For example:
> MLflow — healthy, 3 models registered, alias `production` on v2
> Prefect — `ames-housing-2min` deployment running every 2 min

This matters because a task can be marked `[x]` even if the service had a bug
that was fixed later. The SESSION file records what was *actually* working at
the end of the session.

**4. Bugs fixed during the session**
Every non-trivial bug that was discovered and fixed. For example:
> `src/api/main.py` — Prefect flow_runs/filter body keys were wrong.
> Used `"deployment_filter"` but correct key is `"deployments"`.
> Silent failure returned only SCHEDULED runs, not completed ones.

This is a summary of what's in LESSONS_LEARNED.md — the key things you'd want
to know if something breaks again.

**5. The exact next step**
Not "continue with Group 11" but the precise instruction to paste at the start
of the next session:
> "Read `SESSION_2026-07-11_groups1-10.md` and continue with Group 11.
> Run `/opsx:explore` first."

This one line is the most important part of the file. It eliminates all
ambiguity about where to resume.

---

### How to use them

**Starting a new session:**
1. Open the most recent SESSION file (highest date in the filename)
2. Read the status table — know immediately what's done and what isn't
3. Copy the "exact next step" instruction and paste it as your first message
4. Skip re-reading git log, re-running checks, or re-deriving state — it's all there

**During a session:**
You don't interact with the SESSION file while working. It's read once at the start,
then set aside. All work happens against tasks.md.

**At the end of a session:**
A new SESSION file is written after the final commit (enforced by Hook 2 — see section 4).
It replaces the old one as the "current" handoff document. Old SESSION files are kept
in the repo as a history of how the project progressed.

---

### Naming convention

```
SESSION_YYYY-MM-DD_<topic>.md
```

The date makes it easy to find the latest one. The topic describes what milestone
was reached — e.g. `groups1-10` (Groups 1–10 done) or `complete` (everything done).

---

### Files in this repo

| File | What it records |
|------|----------------|
| `SESSION_2026-07-11_groups1-10.md` | Groups 1–10 complete. Exact handoff instructions for starting Group 11. |
| `SESSION_2026-07-11_complete.md` | All 11 groups done. Stack verified. OpenSpec archived. Final state of the project. |

---

### Why not just use git log?

Git log tells you *what* changed. SESSION files tell you *where you are* and *what to do next*.

A git log entry like `"fix: Prefect flow_runs filter keys"` tells you a fix was made.
The SESSION file tells you the fix was verified working, which endpoint it affected,
what the wrong and right values were, and that the overall stack was healthy after the fix.

They serve different purposes — git log is the audit trail, SESSION files are the
working memory.

---

## 4. The Claude Hooks

This project uses Claude Code (an AI coding assistant) with custom hooks that enforce
deterministic, disciplined behaviour. The hooks are Python scripts that run automatically
before and after certain actions.

They live in `.claude/hooks/` and are wired up in `.claude/settings.json`.

### The problem hooks solve

AI assistants are fast but inconsistent. Left to itself, Claude might:
- Write code without a corresponding task (no traceability)
- Commit code without updating the documentation
- Forget to write a SESSION file at the end of a session
- Skip the post-task checklist when in flow
- Lose track of project rules after a long conversation gets compressed

Hooks make these behaviours **structurally impossible** — they fire automatically,
block the action if something is missing, and tell Claude exactly what to fix.
You don't have to remind Claude every session. The hooks do it.

Think of them like the safety checks on a power tool — you can still use the tool
freely, but it won't let you do something dangerous by accident.

---

### Hook 1 — Task Gate (fires before writing code or committing)

**File:** `.claude/hooks/pre_tool_gate.py`
**Trigger:** Before any file write to `src/`, and before any `git commit`

#### Gate A — No code without a task

**The problem it solves:**
Claude is helpful and will often fix things "while it's there" — touching files
that weren't part of the current task. This is risky: it means untested changes
go in with no record of why, making the codebase hard to audit.

**What it does:**
Before writing any file under `src/`, the hook checks `tasks.md` for a task
marked `[~]` (in-progress). If none exists, it blocks the write and says:

```
BLOCKED: you are about to write to 'src/api/main.py'
but no task is marked [~] in tasks.md.
Steps to fix:
  1. Open tasks.md
  2. Change the relevant task from [ ] to [~]
  3. Then retry the write.
```

**The effect:** Every line of code in this project traces back to an explicit task.
Nothing was written speculatively or "just to fix something quickly".

#### Gate B — No commit without updated docs

**The problem it solves:**
It's very easy to commit code and tell yourself "I'll update LESSONS_LEARNED and
TOI later." Later never comes. After a few sessions, the documentation is weeks
behind the code and useless.

**What it does:**
Before allowing a `git commit`, the hook checks whether `LESSONS_LEARNED.md` and
`TOI.md` were modified *after* the last `src/` file was edited. If either is stale,
it blocks the commit:

```
BLOCKED: git commit is not allowed until LESSONS_LEARNED.md is updated.

Steps to fix:
  1. Append new lessons to LESSONS_LEARNED.md (step 4 of checklist)
  2. Append new commands to TOI.md (step 5 of checklist)
  3. Then retry git commit.
```

**The effect:** Documentation is always in sync with the code. The commit is the
signal that everything — code AND docs — is done.

---

### Hook 2 — SESSION File Check (fires after every git commit)

**File:** `.claude/hooks/post_commit_check.py`
**Trigger:** After every `git commit`

**The problem it solves:**
SESSION files are the handoff brief for the next conversation. Without one, the
next session starts cold — Claude has to re-read git log, re-check which tasks are
done, and re-derive state that could have been written down in 2 minutes. This
wastes 10–15 minutes at the start of every session.

The natural time to write a SESSION file is right after a commit — when everything
is fresh. But it's also the time when you're most tempted to say "done!" and close
the laptop.

**What it does:**
After every `git commit`, the hook checks whether a `SESSION_*.md` file exists and
whether it's newer than the commit. If not, it injects a hard-stop into Claude's
context:

```
HARD GATE — DO NOT PROCEED:
  SESSION file is older than the latest git commit.
  You MUST write a fresh SESSION_YYYY-MM-DD_<topic>.md checkpoint file NOW.
  Include: groups done, last commit hash, key output files, exact next step.
  Then git commit it.
  Only after that is the group truly complete.
```

**The effect:** Every session ends with a fresh SESSION file. The next session
opens it first and picks up exactly where things left off.

---

### Hook 3 — Post-Task Checklist (fires when Claude finishes a response)

**File:** `.claude/hooks/post_task_check.sh`
**Trigger:** When Claude stops generating a response (Stop event)

**The problem it solves:**
The 7-step post-task checklist is defined in `CLAUDE.md`. Claude reads it at the
start of a session but forgets it when deep in implementation. Steps 4, 5, and 6
(update LESSONS_LEARNED, TOI, design.md) are the ones most often skipped.

**What it does:**
After every Claude response, the checklist is printed back into Claude's context
as a visible reminder:

```
POST-COMMIT CHECKLIST (CLAUDE.md — mandatory)
  1. Run the code — confirm real output
  2. Verify outputs — file shapes, row counts, nulls
  3. [x] tasks.md — checkbox marked
  4. LESSONS_LEARNED.md — non-trivial problems appended
  5. TOI.md — useful commands appended
  6. design.md — design decisions recorded
  7. Git commit — done ✓ (you are here)
  8. SESSION file — if group boundary, write and commit
```

**The effect:** Claude sees the checklist after every response and self-corrects
if any step was missed — without the user having to say anything.

---

### Hook 4 — Memory Reload after Context Compression (global)

**Location:** `~/.claude/settings.json` (applies to all projects)
**Trigger:** After Claude's context is auto-compacted

**The problem it solves:**
When a conversation gets very long (thousands of lines of tool calls and responses),
Claude Code automatically compresses older messages into a summary to free up space.
This is called "compaction." After compaction, Claude continues the conversation —
but it no longer has the full text of earlier messages, only the summary.

The risk: project rules defined in memory files (like "never claim something is
fixed without verifying it" or "always update design.md") may not survive the
summary intact. Claude might silently drop enforced behaviours after a compaction.

**What it does:**
After every compaction, the hook fires and prints a reminder into Claude's context:

```
CHECKPOINT COMPLETE - Reloading core memory files...
RELOAD REQUIRED:
  - enforcement_protocol_shared.md
  - PROJECT.md for current project
(Memory files reloaded for next phase)
```

This tells Claude to explicitly re-read the memory files before continuing, so
the rules stay active across the context boundary.

**The effect:** Consistent behaviour throughout a long session, even after the
conversation has been compressed multiple times.

---

## 5. Key Files Reference

| File | What it is |
|------|-----------|
| `CLAUDE.md` | Rules Claude must follow in this project (OpenSpec enforcement, no cheating, comment style, etc.) |
| `LESSONS_LEARNED.md` | Every non-trivial bug fixed during development — what happened, why, and the fix |
| `TOI.md` | Transfer of Information — useful commands accumulated during development |
| `openspec/changes/archive/2026-07-11-build-house-price-app/design.md` | Full design decision log |
| `openspec/changes/archive/2026-07-11-build-house-price-app/tasks.md` | Full 60-task checklist |
| `.claude/hooks/pre_tool_gate.py` | Task gate + commit gate hook |
| `.claude/hooks/post_commit_check.py` | SESSION file check hook |
| `.claude/settings.json` | Hook wiring for this project |
