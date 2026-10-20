#!/bin/bash
# run window scans one after another (one scanning process at a time)
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
while pgrep -f "python3 winscan.py" >/dev/null; do sleep 5; done
for n in "$@"; do python3 winscan.py win_$n.json scan_$n.jsonl > scan_$n.log 2>&1; echo "$n done" >> runq.log; done
