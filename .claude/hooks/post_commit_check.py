#!/usr/bin/env python3
"""
PostToolUse hook: fires after every Bash tool call.
If the command was a git commit, check whether the SESSION file
is up to date. If not, inject a hard reminder into Claude's context.
"""

import sys
import json
import os
import glob

# Read the tool call details from stdin
try:
    tool_call = json.load(sys.stdin)
except Exception:
    # Can't parse — fail open
    sys.exit(0)

# Only care about Bash tool calls
if tool_call.get("tool_name") != "Bash":
    sys.exit(0)

# Only care if the command contained "git commit"
command = tool_call.get("tool_input", {}).get("command", "")
if "git commit" not in command:
    sys.exit(0)

# A git commit just happened — now check if SESSION file is fresh
CWD = "/Users/dvksuman/API"

# Get the timestamp of the latest git commit
import subprocess
r = subprocess.run(
    ["git", "log", "-1", "--format=%ct"],
    capture_output=True, text=True, cwd=CWD
)
last_commit_ts = float(r.stdout.strip()) if r.stdout.strip() else 0.0

# Find all SESSION files
sessions = glob.glob(os.path.join(CWD, "SESSION_*.md"))

# Determine if SESSION file needs to be written
needs_session = False
reason = ""

if not sessions:
    # No SESSION file exists at all
    needs_session = True
    reason = "No SESSION_*.md file found."
else:
    # Check if the newest SESSION file predates the latest commit
    newest_ts = max(os.path.getmtime(f) for f in sessions)
    newest_name = os.path.basename(max(sessions, key=os.path.getmtime))
    if newest_ts < last_commit_ts:
        needs_session = True
        reason = f"SESSION file ({newest_name}) is older than the latest git commit."

if needs_session:
    # Inject a hard reminder — Claude must act on this before doing anything else
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "HARD GATE — DO NOT PROCEED:\n"
                f"  {reason}\n"
                "  You MUST write a fresh SESSION_YYYY-MM-DD_<topic>.md checkpoint file NOW.\n"
                "  Include: groups done, last commit hash, key output files, exact next step.\n"
                "  Then git commit it.\n"
                "  Only after that is the group truly complete."
            )
        }
    }
    print(json.dumps(out))
