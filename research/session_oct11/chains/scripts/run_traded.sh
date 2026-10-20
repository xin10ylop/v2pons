#!/bin/bash
# Second pass: 20 most recent launches that drew >=1 external swap within W (scan up to 200 recent launches).
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
O=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/out
U=https://base-rpc.publicnode.com; PM=0x498581fF718922c3f8e6A244956aF099B2652b2b
C="--chain base --url $U --creations $O/creations_base.jsonl --span 10000 --depth 9800 --W 900 --bt 2 --n 20 --cap 30 --traded_only 200"
python3 -I $S/sample.py $C --venue v4_zora_traded --kind v4 --address $PM --hooks 0x0469a4bd3724dc86c9542f4694c976da13c450c0
python3 -I $S/sample.py $C --venue v4_doppler_traded --kind v4 --address $PM --hooks 0xbdf938149ac6a781f94faa0ed45e6a0e984c6544
python3 -I $S/sample.py $C --venue v4_clanker_traded --kind v4 --address $PM --hooks 0xb429d62f8f3bffb98cdb9569533ea23bf0ba28cc
python3 -I $S/sample.py $C --venue v4_nohook_traded --kind v4 --address $PM --hooks 0x0000000000000000000000000000000000000000
C="--chain bnb --url https://bsc-rpc.publicnode.com --span 5000 --depth 9800 --W 1200 --bt 0.45 --n 20 --cap 30 --traded_only 200"
python3 -I $S/sample.py $C --venue fourmeme_traded --kind fourmeme --address 0x5c952063c7fc8610FFDB798152D69F0B9550762b
python3 -I $S/sample.py $C --venue pcs_v2_traded --kind v2 --address 0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73
python3 -I $S/sample.py $C --venue uni_v4_traded --kind v4 --address 0x28e2Ea090877bF75740558f6BFB36A5ffeE9e9dF
echo ALLDONE
