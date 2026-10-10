#!/bin/bash
cd /tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins
echo "== Q2b fill fwd 83552000->83600000 stop 0xe7a1c2fb (where crowd B's 5.67 ETH went after the 19:11 curve)"
python3 fill.py 83552000 83600000 forward 0xe7a1c2fb86bd4755254a1f8de24e50ccc34c662e
echo "== Q3 fill back 83456249->83403250 stop 0x6bce9c1c"
python3 fill.py 83403250 83456249 backward 0x6bce9c1cfdf71e70f16d0999091b2a6dc016c902
echo "== A0 fill back 81818499->81760000 stop 0x4268b546 (A pre-genesis deployer funding)"
python3 fill.py 81760000 81818499 backward 0x4268b54646f1211b7475c9618fd4333d32f13379
echo "== Q5 fill fwd 83319750->83360415 stop 0x9614ea90"
python3 fill.py 83319750 83360415 forward 0x9614ea90533fe312c36a09a9fdfacb6b09b267cd
echo "== QUEUE7 DONE"
