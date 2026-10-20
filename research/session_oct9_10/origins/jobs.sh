#!/bin/bash
# sequential job runner: executes lines appended to jobs.q (one at a time), after the earlier queues finish
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
while pgrep -f "runq.sh r8" >/dev/null || pgrep -f "runq2.sh d19" >/dev/null || pgrep -f "python3 winscan.py" >/dev/null; do sleep 5; done
touch jobs.q jobs.done
while true; do
  n=$(wc -l < jobs.done)
  line=$(sed -n "$((n+1))p" jobs.q)
  if [ -z "$line" ]; then sleep 3; continue; fi
  echo "START $(date +%T) $line" >> jobs.log
  bash -c "$line" >> jobs.log 2>&1
  echo "$line" >> jobs.done
  echo "END $(date +%T)" >> jobs.log
done
