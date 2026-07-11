#!/usr/bin/env python3
"""
Stop hook — CLAUDE.md post-task checklist (all 7 steps).

Fires after every Claude response and injects reminders for any steps not done.

Steps checked:
  3. tasks.md           — warn if any [~] items remain (started but not [x])
  4. LESSONS_LEARNED.md — warn if older than the last src/ file edit
  5. TOI.md             — warn if older than the last src/ file edit
  6. design.md          — warn if older than the last src/ file edit
  7. git commit         — warn if tracked files have uncommitted changes
  +  SESSION checkpoint — remind if missing or older than last commit
"""

import subprocess, os, json, glob

CWD = "/Users/dvksuman/API"
msgs = []


def mtime(path):
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return 0.0


def last_commit_ts():
    r = subprocess.run(["git", "log", "-1", "--format=%ct"],
                       capture_output=True, text=True, cwd=CWD)
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def last_src_edit_ts():
    src_files = glob.glob(os.path.join(CWD, "src", "**", "*.py"), recursive=True)
    return max((os.path.getmtime(f) for f in src_files), default=0.0)


# ── Check 3: tasks.md — any [~] still open? ────────────────────────────────
tasks_path = os.path.join(CWD, "openspec", "changes", "build-house-price-app", "tasks.md")
if os.path.exists(tasks_path):
    with open(tasks_path) as f:
        content = f.read()
    in_progress = [l.strip() for l in content.splitlines() if l.strip().startswith("- [~]")]
    if in_progress:
        items = "\n".join(f"      {t}" for t in in_progress)
        msgs.append(f"tasks.md has [~] in-progress items — mark [x] when done:\n{items}")


# ── Checks 4/5/6: doc files vs last src/ edit ──────────────────────────────
src_ts = last_src_edit_ts()
if src_ts > 0:
    docs = {
        "LESSONS_LEARNED.md": os.path.join(CWD, "LESSONS_LEARNED.md"),
        "TOI.md":             os.path.join(CWD, "TOI.md"),
        "design.md":          os.path.join(CWD, "openspec", "changes", "build-house-price-app", "design.md"),
    }
    for name, path in docs.items():
        if mtime(path) < src_ts:
            msgs.append(f"{name} not updated since last src/ edit (steps 4/5/6) — append lessons/commands/decisions.")


# ── Check 7: uncommitted changes in tracked files ──────────────────────────
r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=CWD)
dirty = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("??")]
if dirty:
    preview = "\n".join(f"      {l}" for l in dirty[:8]) + ("\n      ..." if len(dirty) > 8 else "")
    msgs.append(f"Uncommitted changes (step 7 — git commit):\n{preview}")


# ── Bonus: SESSION checkpoint ───────────────────────────────────────────────
sessions = glob.glob(os.path.join(CWD, "SESSION_*.md"))
commit_ts = last_commit_ts()
if not sessions:
    msgs.append("No SESSION_*.md found — write a checkpoint before /clear.")
else:
    newest = max(sessions, key=os.path.getmtime)
    if os.path.getmtime(newest) < commit_ts:
        msgs.append(f"SESSION checkpoint ({os.path.basename(newest)}) predates last commit — update it before /clear.")


# ── Emit if anything outstanding ───────────────────────────────────────────
if msgs:
    bar = "─" * 55
    body = (
        f"\n{bar}\nPOST-TASK CHECKLIST — items outstanding:\n{bar}\n"
        + "\n\n".join(f"  [{i+1}] {m}" for i, m in enumerate(msgs))
        + f"\n{bar}\nComplete these before starting the next task.\n{bar}"
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": body}}))
