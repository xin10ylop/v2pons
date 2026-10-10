#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
until grep -q "== Q5" queue9.log; do sleep 5; done
for p in $(ps -eo pid,args | awk '/[q]ueue9\.sh|[f]ill\.py 83319750/ {print $1}'); do kill $p; done
echo "== Q2d fill fwd 83557500->83640000 stop FROM 0xe7a1c2fb (nonces 6-8)"
python3 fill.py 83557500 83640000 forward 0xe7a1c2fb86bd4755254a1f8de24e50ccc34c662e from
echo "== Q2e fill fwd 83557500->83600000 stop FROM 0x639266c3"
python3 fill.py 83557500 83600000 forward 0x639266c3f6758e81ff3ac80e6e0b269e99c636b5 from
echo "== QUEUE10 DONE"
