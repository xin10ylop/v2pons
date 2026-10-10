#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
until grep -q "== Q5" queue8.log; do sleep 5; done
for p in $(ps -eo pid,args | awk '/[q]ueue8\.sh|[f]ill\.py 83319750/ {print $1}'); do kill $p; done
echo "== G3 fill back 84028249->83997000 stop 0xa57fb285 (Oct 9 09:24 deployer funding)"
python3 fill.py 83997000 84028249 backward 0xa57fb285237f62ada4e9265e89321822e1719f98
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE9 DONE"
