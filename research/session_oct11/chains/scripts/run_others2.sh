#!/bin/bash
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
O=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/out
python3 -I $S/sample.py --chain unichain --url https://mainnet.unichain.org --creations $O/creations_unichain.jsonl --span 10000 --W 3600 --bt 1 --n 20 --cap 30 --venue v4_all --kind v4 --address 0x1F98400000000000000000000000000000000004
python3 -I $S/sample.py --chain ink --url https://rpc-qnd.inkonchain.com --creations $O/creations_ink.jsonl --span 10000 --W 3600 --bt 1 --n 20 --cap 30 --traded_only 485 --venue v4_nohook_traded --kind v4 --address 0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32 --hooks 0x0000000000000000000000000000000000000000
echo ALLDONE
