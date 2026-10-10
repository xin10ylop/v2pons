#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
until grep -q "== Q5" queue7.log; do sleep 5; done
for p in $(ps -eo pid,args | awk '/[q]ueue7\.sh|[f]ill\.py 83319750/ {print $1}'); do kill $p; done
echo "== Q2c fill fwd 83552250->83640000 stop FROM 0xe7a1c2fb (its nonces 5-8: where ~1.3 ETH of the B pot went)"
python3 fill.py 83552250 83640000 forward 0xe7a1c2fb86bd4755254a1f8de24e50ccc34c662e from
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE8 DONE"
