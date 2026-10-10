#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/eras
while read s rest; do
  [ -z "$s" ] && continue
  timeout 1500 python3 -u $s $rest >> q2.txt 2>&1
  echo "DONE $s $rest $(date +%T)" >> runq2.log
done < ${1:-queue2.txt}
echo ALLDONE >> runq2.log
