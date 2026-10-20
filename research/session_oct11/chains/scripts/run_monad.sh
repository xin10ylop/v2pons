#!/bin/bash
# Monad public RPC caps eth_getLogs at 100 blocks -> 1h window (12k blocks) extrapolated to 24h; W = 600 blocks (~3 min).
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
C="--chain monad --url https://rpc.monad.xyz --span 100 --hours 1 --W 600 --n 20 --cap 30"
python3 -I $S/sample.py $C --venue nadfun_curve --kind nadfun --address 0xA7283d07812a02AFB7C09B60f8896bCEA3F90aCE
python3 -I $S/sample.py $C --venue uni_v4 --kind v4 --address 0x188d586Ddcf52439676Ca21A244753fA19F9Ea8e
python3 -I $S/sample.py $C --venue uni_v3 --kind v3 --address 0x204FAca1764B154221e35c0d20aBb3c525710498
python3 -I $S/sample.py $C --venue nadfun_dex_v3 --kind v3 --address 0x6B5F564339DbAD6b780249827f2198a841FEB7F3
echo ALLDONE
