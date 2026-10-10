#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/eras
while read b t; do
  python3 -u trace.py $b 700 450 $t >> traces.txt 2>&1
  echo "DONE $b $t $(date +%T)" >> runq.log
done < queue.txt
echo ALLDONE >> runq.log
