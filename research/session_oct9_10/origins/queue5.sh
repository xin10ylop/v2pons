#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
until grep -q "== Q2" queue4.log; do sleep 5; done
for p in $(ps -eo pid,args | awk '/[q]ueue4\.sh|[f]ill\.py 83518500/ {print $1}'); do kill $p; done
echo "== BG back-trace B crowd genesis: 0x5777452e from 65415799"
(cd ../ops/lch && python3 loopback.py 0x5777452ec62463a39e9e28525db94027c51bd626 65415799 8 50000000 /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/bgen_back.jsonl)
echo "== Q2 fill fwd 83518500->83552000"
python3 fill.py 83518500 83552000 forward
echo "== Q3 fill back 83456249->83403250 stop 0x6bce9c1c"
python3 fill.py 83403250 83456249 backward 0x6bce9c1cfdf71e70f16d0999091b2a6dc016c902
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE5 DONE"
