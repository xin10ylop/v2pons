#!/bin/bash
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
O=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/out
# Ink (24h creations from discovery; 1s blocks; W = 1h)
C="--chain ink --url https://rpc-qnd.inkonchain.com --creations $O/creations_ink.jsonl --span 10000 --W 3600 --bt 1 --n 20 --cap 30"
python3 -I $S/sample.py $C --venue v4_nohook --kind v4 --address 0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32 --hooks 0x0000000000000000000000000000000000000000
python3 -I $S/sample.py $C --venue v4_sentrystock --kind v4 --address 0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32 --hooks 0x976697adcf27d0962d3b0b6304d5975ba647b0cc
# OP Mainnet
python3 -I $S/sample.py --chain optimism --url https://mainnet.optimism.io --creations $O/creations_optimism.jsonl --span 10000 --W 1800 --bt 2 --n 20 --cap 30 --venue v4_all --kind v4 --address 0x9a13F98Cb987694C9F086b1F5eB990EeA8264Ec3
# Unichain
python3 -I $S/sample.py --chain unichain --url https://mainnet.unichain.org --creations $O/creations_unichain.jsonl --span 10000 --W 3600 --bt 1 --n 20 --cap 30 --venue v4_all --kind v4 --address 0x1F98400000000000000000000000000000000004
# MegaETH: address-filtered 24h fetch (cross-check of the no-address discovery)
C="--chain megaeth --url https://mainnet.megaeth.com/rpc --span 20000 --W 3600 --bt 1 --n 20 --cap 30"
python3 -I $S/sample.py $C --venue kumbaya_launchpad --kind kumbaya --address 0x69FE0908F1211dE66F7067021998f28A5693ABbD
python3 -I $S/sample.py $C --venue kumbaya_v3 --kind v3 --address 0x68b34591f662508076927803c567Cc8006988a09
python3 -I $S/sample.py $C --venue v4_all --kind v4 --address 0xaCB7e78fa05D562e0A5D3089ec896D57D057d38E
python3 -I $S/sample.py $C --venue univ3 --kind v3 --address 0x3a5F0CD7d62452b7f899B2A5758BFa57be0dE478
# block-time probe retry for Soneium
python3 -I $S/probe.py soneium
echo ALLDONE
