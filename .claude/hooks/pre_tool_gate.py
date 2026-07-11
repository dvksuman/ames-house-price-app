#!/usr/bin/env python3
"""
PreToolUse hook — two gates:

Gate 1 (Write/Edit/NotebookEdit): block writes to src/ unless a [~] task exists.
Gate 2 (Bash): block `git commit` unless LESSONS_LEARNED.md and TOI.md
               were modified more recently than the last src/ file edit.
               This forces doc updates BEFORE the commit, not after.

Exit 2 = block the tool and show the message to Claude.
Exit 0 = allow the tool to proceed.
"""

import sys
import json
import os
import glob

# Read the tool call details that Claude Code sends on stdin.
try:
    tool_call = json.load(sys.stdin)
except Exception:
    # If we can't parse stdin, don't block — fail open.
    sys.exit(0)

# Get the tool name and its input arguments.
tool_name = tool_call.get("tool_name", "")
tool_input = tool_call.get("tool_input", {})

# Absolute path to the project root.
PROJECT_ROOT = "/Users/dvksuman/API"


def mtime(path):
    """Return the file's last-modified timestamp, or 0 if it doesn't exist."""
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return 0.0


def last_src_edit_ts():
    """Return the most recent modification time of any .py file under src/."""
    src_files = glob.glob(os.path.join(PROJECT_ROOT, "src", "**", "*.py"), recursive=True)
    return max((os.path.getmtime(f) for f in src_files), default=0.0)


# ===========================================================================
# GATE 2: block `git commit` if LESSONS_LEARNED or TOI are stale
# ===========================================================================
if tool_name == "Bash":
    command = tool_input.get("command", "")

    # Only intercept git commit commands — ignore all other Bash calls.
    if "git commit" in command:
        src_ts = last_src_edit_ts()

        # Paths to the two doc files that must be updated after every src/ edit.
        lessons_path = os.path.join(PROJECT_ROOT, "LESSONS_LEARNED.md")
        toi_path = os.path.join(PROJECT_ROOT, "TOI.md")

        stale = []

        # Check LESSONS_LEARNED.md — block if older than last src/ edit.
        if mtime(lessons_path) < src_ts:
            stale.append("LESSONS_LEARNED.md")

        # Check TOI.md — block if older than last src/ edit.
        if mtime(toi_path) < src_ts:
            stale.append("TOI.md")

        if stale:
            # Build a clear error message listing exactly what needs updating.
            files_list = " and ".join(stale)
            print(
                f"BLOCKED: git commit is not allowed until {files_list} "
                f"{'are' if len(stale) > 1 else 'is'} updated.\n\n"
                f"The following {'files have' if len(stale) > 1 else 'file has'} "
                f"not been updated since the last src/ edit:\n"
                + "".join(f"  - {f}\n" for f in stale)
                + "\nSteps to fix:\n"
                f"  1. Append new lessons to LESSONS_LEARNED.md (step 4 of checklist)\n"
                f"  2. Append new commands to TOI.md (step 5 of checklist)\n"
                f"  3. Then retry git commit.\n\n"
                f"This block exists so you never need to remind Claude again."
            )
            sys.exit(2)

    # All other Bash commands — allow.
    sys.exit(0)


# ===========================================================================
# GATE 1: block writes to src/ unless a [~] task exists in tasks.md
# ===========================================================================

# Only care about file-writing tools.
writing_tools = {"Write", "Edit", "NotebookEdit"}
if tool_name not in writing_tools:
    sys.exit(0)

# Get the file path being written.
file_path = tool_input.get("file_path", "")

# Normalise to a relative path for comparison.
try:
    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
except ValueError:
    sys.exit(0)

# Only enforce for files under src/.
if not rel_path.startswith("src" + os.sep) and not rel_path.startswith("src/"):
    sys.exit(0)

# Find the active tasks.md for the open change.
tasks_files = glob.glob(
    os.path.join(PROJECT_ROOT, "openspec", "changes", "*", "tasks.md")
)

if not tasks_files:
    sys.exit(0)

# Use the most recently modified tasks.md (in case there are multiple changes).
tasks_file = max(tasks_files, key=os.path.getmtime)

# Read it and look for any [~] line.
try:
    with open(tasks_file, "r") as f:
        content = f.read()
except OSError:
    sys.exit(0)

if "[~]" in content:
    sys.exit(0)

# No [~] task found — block the write.
print(
    f"BLOCKED by PreToolUse gate: you are about to write to '{rel_path}' "
    f"but no task is marked [~] (in-progress) in tasks.md.\n"
    f"Steps to fix:\n"
    f"  1. Open {os.path.relpath(tasks_file, PROJECT_ROOT)}\n"
    f"  2. Change the relevant task from [ ] to [~]\n"
    f"  3. Then retry the write."
)
sys.exit(2)
