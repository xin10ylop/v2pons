#!/bin/bash
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
O=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/out
U=https://base-rpc.publicnode.com; PM=0x498581fF718922c3f8e6A244956aF099B2652b2b
C="--chain base --url $U --creations $O/creations_base.jsonl --span 10000 --depth 9800 --W 900 --bt 2 --n 20 --cap 30"
python3 -I $S/sample.py $C --venue v4_zora --kind v4 --address $PM --hooks 0x0469a4bd3724dc86c9542f4694c976da13c450c0
python3 -I $S/sample.py $C --venue v4_hook87a4 --kind v4 --address $PM --hooks 0x87a4e12530071269f0671a2f064afffbfe74eaec
python3 -I $S/sample.py $C --venue v4_doppler --kind v4 --address $PM --hooks 0xbdf938149ac6a781f94faa0ed45e6a0e984c6544
python3 -I $S/sample.py $C --venue v4_clanker --kind v4 --address $PM --hooks 0xb429d62f8f3bffb98cdb9569533ea23bf0ba28cc
python3 -I $S/sample.py $C --venue v4_nohook --kind v4 --address $PM --hooks 0x0000000000000000000000000000000000000000
python3 -I $S/sample.py $C --venue univ2 --kind v2 --address 0x8909dc15e40173ff4699343b6eb8132c65e18ec6
python3 -I $S/sample.py $C --venue v2_02a84c1b --kind v2 --address 0x02a84c1b3bbd7401a5f7fa98a384ebc70bb5749e
python3 -I $S/sample.py $C --venue slipstream_f8f2 --kind v3 --address 0xf8f2eb4940cfe7d13603dddd87f123820fc061ef
python3 -I $S/sample.py $C --venue aero_v2 --kind solidly --address 0x420dd381b31aef6683db6b902084cb0ffece40da
python3 -I $S/prices.py
echo ALLDONE
