#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
while pgrep -f "loopback.py 0x9614ea90" >/dev/null; do sleep 5; done
echo "== Q1 fill back 83240749->83225000 stop 0x1a687e8d" 
python3 fill.py 83225000 83240749 backward 0x1a687e8def32214b3644edf4fb21c4440b508fde
echo "== Q2 fill fwd 83518500->83552000"
python3 fill.py 83518500 83552000 forward
echo "== Q3 fill back 83456249->83403250 stop 0x6bce9c1c"
python3 fill.py 83403250 83456249 backward 0x6bce9c1cfdf71e70f16d0999091b2a6dc016c902
echo "== QUEUE DONE"
