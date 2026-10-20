#!/bin/bash
# the rest of stage 1 after the disk-full stop: the transactions (3 passes), the build, the fronters' table, the ETH price, the wallets,
# the + 1 bot's funding (one RPC process at a time); no backward extension
cd /home/user/v2pons/research/session_oct12/crowd/reaction
(python3 r03_txs.py && python3 r03_txs.py && python3 r03_txs.py) > r03_txs.out 2>&1
python3 r04_build.py > r04_build.out 2>&1; python3 r08_fronters.py > r08_fronters.out 2>&1
python3 r10_ethusd.py > r10_ethusd.out 2>&1; python3 r13_wallets.py > r13_wallets.out 2>&1; python3 r18_bot_funding.py > r18_bot_funding.out 2>&1
echo STAGE1_DONE > stage1.flag
