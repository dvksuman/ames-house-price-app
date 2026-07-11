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

SESSION files are handoff documents — written at the end of each work session so
the next session can pick up exactly where things left off without re-deriving state.

### What they contain

Each SESSION file has:
- Which task groups are complete
- The last git commit hash
- Key things that were verified working
- Bugs that were fixed
- The **exact next step** — which group, which task number

### How to use them

At the start of a new session:
1. Read the SESSION file first (before anything else)
2. Use the "Exact next step" section to know where to continue
3. Skip re-reading git log, re-running checks, or re-deriving state — it's all there

### Files in this repo

| File | Covers |
|------|--------|
| `SESSION_2026-07-11_groups1-10.md` | Groups 1–10 complete, handoff to Group 11 |
| `SESSION_2026-07-11_complete.md` | All groups done, stack verified, OpenSpec archived |

---

## 4. The Claude Hooks

This project uses Claude Code (an AI coding assistant) with custom hooks that enforce
deterministic, disciplined behaviour. The hooks are Python scripts that run automatically
before and after certain actions.

They live in `.claude/hooks/` and are wired up in `.claude/settings.json`.

### Hook 1 — PreToolUse: Task Gate (`pre_tool_gate.py`)

**When it fires:** Before any file write (`Write`, `Edit`) to the `src/` directory,
and before any `git commit`.

**What it does (Gate 1 — writes):**
Blocks writes to `src/` unless a task is marked `[~]` (in-progress) in `tasks.md`.
This prevents Claude from writing code speculatively — every line of code must trace
back to an explicit task.

**What it does (Gate 2 — commits):**
Blocks `git commit` if `LESSONS_LEARNED.md` or `TOI.md` haven't been updated since
the last `src/` file was edited. This forces documentation to happen before the commit,
not after (when it gets forgotten).

**Why it exists:** Without this gate, Claude (and humans) tend to commit code and
promise to "update the docs later". Later never comes. The hook makes it structurally
impossible to skip.

### Hook 2 — PostToolUse: SESSION File Check (`post_commit_check.py`)

**When it fires:** After every `git commit`.

**What it does:**
Checks whether a SESSION file exists and whether it's newer than the latest commit.
If not, it injects a hard reminder into Claude's context: "HARD GATE — write a
SESSION file NOW before doing anything else."

**Why it exists:** SESSION files are easy to skip when you're in flow. The hook
makes the omission visible immediately after the commit, while the context is still fresh.

### Hook 3 — Stop: Post-Task Checklist (`post_task_check.sh`)

**When it fires:** When Claude finishes a response (Stop event).

**What it does:**
Prints the 7-step post-task checklist to Claude's context as a reminder:
1. Run the code
2. Verify outputs
3. Mark `[x]` in tasks.md
4. Update LESSONS_LEARNED.md
5. Update TOI.md
6. Update design.md
7. Git commit

**Why it exists:** The checklist is defined in `CLAUDE.md`, but Claude would sometimes
skip steps when working quickly. The hook makes the checklist appear automatically
after every response, so it can't be forgotten.

### Hook 4 — PostCompact: Memory Reload (global settings)

**When it fires:** After Claude's context is auto-compacted (when the conversation
gets very long, older messages are summarized to free up space).

**What it does:**
Prints a reminder to reload core memory files (`enforcement_protocol_shared.md`,
`ROUTING_RULES.md`, project context) so behaviour stays consistent across the
context boundary.

**Why it exists:** When context compacts, Claude starts the next phase without
full memory of earlier instructions. This hook ensures the key rules are reloaded
immediately.

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
