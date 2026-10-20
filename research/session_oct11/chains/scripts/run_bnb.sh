#!/bin/bash
# BNB: publicnode serves logs only for the most recent ~10k blocks (~75 min) -> counts are extrapolated to 24h.
S=/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/chains/scripts
C="--chain bnb --url https://bsc-rpc.publicnode.com --span 5000 --depth 9800 --W 1200 --bt 0.45 --n 20 --cap 30"
python3 -I $S/sample.py $C --venue fourmeme --kind fourmeme --address 0x5c952063c7fc8610FFDB798152D69F0B9550762b
python3 -I $S/sample.py $C --venue pcs_v2 --kind v2 --address 0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73
python3 -I $S/sample.py $C --venue pcs_v3 --kind v3 --address 0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865
python3 -I $S/sample.py $C --venue pcs_infinity_cl --kind pcsinf --address 0xa0FfB9c1CE1Fe56963B0321B32E7A0302114058b
python3 -I $S/sample.py $C --venue uni_v4 --kind v4 --address 0x28e2Ea090877bF75740558f6BFB36A5ffeE9e9dF
python3 -I $S/sample.py $C --venue uni_v3 --kind v3 --address 0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7
python3 -I $S/sample.py $C --venue uni_v2 --kind v2 --address 0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6
echo ALLDONE
