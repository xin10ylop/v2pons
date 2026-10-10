#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
echo "== Q1 fill back 83240749->83225000 stop 0x1a687e8d"
python3 fill.py 83225000 83240749 backward 0x1a687e8def32214b3644edf4fb21c4440b508fde
echo "== AG back-trace A genesis funder 0x4268b546 from 81833714"
(cd ../ops/lch && python3 loopback.py 0x4268b54646f1211b7475c9618fd4333d32f13379 81833714 8 70000000 /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/agen_back.jsonl)
echo "== Q2 fill fwd 83518500->83552000"
python3 fill.py 83518500 83552000 forward
echo "== Q3 fill back 83456249->83403250 stop 0x6bce9c1c"
python3 fill.py 83403250 83456249 backward 0x6bce9c1cfdf71e70f16d0999091b2a6dc016c902
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE4 DONE"
