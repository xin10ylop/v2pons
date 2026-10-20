#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
until grep -q "== Q3" queue5.log; do sleep 5; done
# pause queue5 (Q3/Q5) while A0 runs: kill it, re-run the remainder afterwards
for p in $(ps -eo pid,args | awk '/[q]ueue5\.sh|[f]ill\.py 83403250/ {print $1}'); do kill $p; done
echo "== A0 fill back 81818499->81760000 stop 0x4268b546 (A pre-genesis deployer funding)"
python3 fill.py 81760000 81818499 backward 0x4268b54646f1211b7475c9618fd4333d32f13379
echo "== Q3 fill back 83456249->83403250 stop 0x6bce9c1c"
python3 fill.py 83403250 83456249 backward 0x6bce9c1cfdf71e70f16d0999091b2a6dc016c902
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE6 DONE"
