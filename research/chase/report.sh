#!/bin/bash
# report.sh [SINCE="YYYY-mm-dd HH:MM" UTC]: where the operator is, chain by chain, from public RPCs. Every v4 pool paired with the
# native coin (and WETH/WBNB on Base and BNB) since SINCE, grouped by launch contract, hook and tick spacing with liquidity and pulls;
# every V2 pair on the factories the pump-and-pull lines use. Output under research/chase/out/<date>/. Takes 20-60 minutes.
#     bash research/chase/report.sh "2026-10-20 00:00"
set -u; HERE="$(cd "$(dirname "$0")" && pwd)"; SINCE="${1:-$(date -u -d '-24 hours' '+%Y-%m-%d %H:%M')}"; OUT="$HERE/out/$(date -u +%Y%m%dT%H%M)"; mkdir -p "$OUT"; cd "$OUT"
RH=https://rpc.mainnet.chain.robinhood.com; BASE=https://open-platform.nodereal.io/64a9df0874fb4a93b9d0a3849de012d3/base; BASE_TX=https://mainnet.base.org
BNB=https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3; ETH=https://eth-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3
echo "== since $SINCE UTC -> $OUT"
python3 "$HERE/scan.py" robinhood $RH 0x8366a39cc670b4001a1121b8f6a443a643e40951 "$SINCE" rh.json 99999 3000 &
TX_RPC=$BASE_TX python3 "$HERE/scan.py" base $BASE 0x498581fF718922c3f8e6A244956aF099B2652b2b "$SINCE" base.json 5000 150 400000 &
python3 "$HERE/scan.py" bnb $BNB 0x28e2Ea090877bF75740558f6BFB36A5ffeE9e9dF "$SINCE" bnb.json 5000 400 1500000 &
python3 "$HERE/scan.py" ethereum $ETH 0x000000000004444c5dc75cB358380D2e3dE08A90 "$SINCE" eth.json 5000 25 60000 &
wait
PAIR=0x4200000000000000000000000000000000000006 PAIR_POS=2 TX_RPC=$BASE_TX python3 "$HERE/scan.py" base $BASE 0x498581fF718922c3f8e6A244956aF099B2652b2b "$SINCE" base_weth0.json 5000 150 400000 &
PAIR=0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c PAIR_POS=3 python3 "$HERE/scan.py" bnb $BNB 0x28e2Ea090877bF75740558f6BFB36A5ffeE9e9dF "$SINCE" bnb_wbnb.json 5000 400 1500000 &
wait
for f in rh base bnb eth base_weth0 bnb_wbnb; do [ -f $f.json ] && python3 "$HERE/analyze.py" $f.json 2>/dev/null | head -60; done | tee groups.txt
# the operator's v4 launcher on Robinhood, if it launched: every swap in the first 5 minutes, priced
if [ -f rh.json ] && python3 -c "import json,sys; d=json.load(open('rh.json')); sys.exit(0 if any(p['to']=='3194e32622c5d860a0572c74edda99dcfd8fc827' for p in d['pools'].values()) else 1)"; then
  python3 "$HERE/deep.py" 0x3194e32622c5d860a0572c74edda99dcfd8fc827 rh_deep.json rh.json $RH 0x8366a39cc670b4001a1121b8f6a443a643e40951 3000 && python3 "$HERE/price_deep.py" rh_deep.json 0.1 0.02 0.02 2>/dev/null | tee operator_rh.txt
fi
# the V2 pump-and-pull lines: Robinhood factory 0x8bceaa40 (WETH 0xf41eacad73...) and Base's Uniswap V2 factory
RHB=$(python3 - "$SINCE" <<'PY'
import sys, time, calendar; ts = calendar.timegm(time.strptime(sys.argv[1], "%Y-%m-%d %H:%M")); print(max(1, int(93446000 - (1792501200 - ts) * 10)))
PY
)
python3 "$HERE/v2scan.py" $RH 0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f 0xf41eacad73d5ac4066ae25b4b93d0c4a7ccce9fd $RHB rh_v2.json 3000 1500 && python3 "$HERE/v2price.py" rh_v2.json 0x0000000000000000000000000000000000000000 0.1 2>/dev/null | tee v2_rh.txt
echo "== done: $OUT"
