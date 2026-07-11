#!/usr/bin/env python3
"""
Stop hook: after every Claude response, check if CLAUDE.md or SESSION checkpoint
needs attention and inject a reminder into the next turn's context.
"""
import subprocess, os, json, glob, sys

CWD = '/Users/dvksuman/API'
msgs = []

# Check 1: CLAUDE.md uncommitted changes
r = subprocess.run(
    ['git', 'status', '--porcelain', 'CLAUDE.md'],
    capture_output=True, text=True, cwd=CWD
)
if r.stdout.strip():
    msgs.append('CLAUDE.md has uncommitted changes — commit it now (task checklist step 7).')

# Check 2: SESSION checkpoint newer than last commit
r2 = subprocess.run(
    ['git', 'log', '-1', '--format=%ct'],
    capture_output=True, text=True, cwd=CWD
)
last_commit_ts = float(r2.stdout.strip()) if r2.stdout.strip() else 0.0

sessions = glob.glob(os.path.join(CWD, 'SESSION_*.md'))
if not sessions:
    msgs.append('No SESSION_*.md checkpoint file found — write one before /clear.')
else:
    newest_ts = max(os.path.getmtime(f) for f in sessions)
    if newest_ts <= last_commit_ts:
        newest_name = max(sessions, key=os.path.getmtime)
        msgs.append(
            f'SESSION checkpoint ({os.path.basename(newest_name)}) is older than the last git commit — '
            'write a fresh one now.'
        )

if msgs:
    reminder = 'POST-TASK CHECKLIST (auto-check):\n' + '\n'.join(f'  [{i+1}] {m}' for i, m in enumerate(msgs))
    out = {
        'hookSpecificOutput': {
            'hookEventName': 'Stop',
            'additionalContext': reminder
        }
    }
    print(json.dumps(out))
