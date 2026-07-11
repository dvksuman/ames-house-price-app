#!/usr/bin/env python3
"""
PreToolUse hook: before Claude writes or edits any file under src/,
confirm that at least one task is marked [~] (in-progress) in tasks.md.
Exit 2 = block the tool and show the message to Claude.
Exit 0 = allow the tool to proceed.
"""

import sys
import json
import os
import glob

# Read the tool call details that Claude Code sends on stdin
try:
    tool_call = json.load(sys.stdin)
except Exception:
    # If we can't parse stdin, don't block — fail open
    sys.exit(0)

# Get the tool name and the file path argument
tool_name = tool_call.get("tool_name", "")
tool_input = tool_call.get("tool_input", {})

# Only care about file-writing tools
writing_tools = {"Write", "Edit", "NotebookEdit"}
if tool_name not in writing_tools:
    # Not a write tool — always allow
    sys.exit(0)

# Get the file path being written
file_path = tool_input.get("file_path", "")

# Normalise to a relative path for comparison
project_root = "/Users/dvksuman/API"
try:
    rel_path = os.path.relpath(file_path, project_root)
except ValueError:
    # Different drive on Windows — just allow
    sys.exit(0)

# Only enforce for files under src/
if not rel_path.startswith("src" + os.sep) and not rel_path.startswith("src/"):
    sys.exit(0)

# Find the active tasks.md for the open change
tasks_files = glob.glob(
    os.path.join(project_root, "openspec", "changes", "*", "tasks.md")
)

if not tasks_files:
    # No tasks.md found — warn but don't block (project may not have one yet)
    sys.exit(0)

# Use the most recently modified tasks.md (in case there are multiple changes)
tasks_file = max(tasks_files, key=os.path.getmtime)

# Read it and look for any [~] line
try:
    with open(tasks_file, "r") as f:
        content = f.read()
except OSError:
    # Can't read the file — fail open
    sys.exit(0)

if "[~]" in content:
    # At least one task is in-progress — allow the write
    sys.exit(0)

# No [~] task found — block the write
print(
    f"BLOCKED by PreToolUse gate: you are about to write to '{rel_path}' "
    f"but no task is marked [~] (in-progress) in tasks.md.\n"
    f"Steps to fix:\n"
    f"  1. Open {os.path.relpath(tasks_file, project_root)}\n"
    f"  2. Change the relevant task from [ ] to [~]\n"
    f"  3. Then retry the write."
)
sys.exit(2)
