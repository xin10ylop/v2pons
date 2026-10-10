#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/eras
until grep -q ALLDONE runq2.log; do sleep 10; done
sed -i 's/^ALLDONE$/ALLDONE-q2/' runq2.log
./runq2.sh queue3.txt
