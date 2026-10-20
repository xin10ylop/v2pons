#!/bin/bash
# after the first r03 chain (pid $1) exits: build the pools, the fronters' table, the ETH price and the wallets' state (a few calls), then
# extend the launches back to block $2 and fetch their events and transactions (one RPC process at a time)
while kill -0 "$1" 2>/dev/null; do sleep 30; done
cd /home/user/v2pons/research/session_oct12/crowd/reaction
python3 r04_build.py > r04_build.out 2>&1; python3 r08_fronters.py > r08_fronters.out 2>&1
python3 r10_ethusd.py > r10_ethusd.out 2>&1; python3 r13_wallets.py > r13_wallets.out 2>&1
echo STAGE1_DONE > stage1.flag
python3 r01_extend.py "$2" > r01_extend.out 2>&1 && python3 r02_events.py > r02_events_ext.out 2>&1 && \
  (python3 r03_txs.py && python3 r03_txs.py && python3 r03_txs.py) > r03_txs_ext.out 2>&1
echo EXTEND_DONE >> r03_txs_ext.out
