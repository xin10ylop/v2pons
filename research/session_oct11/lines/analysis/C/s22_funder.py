"""The 0f34e3b5 fleet's funder: blocks from the funding transfer to the wallet's buy, the funding vs the buy amount, and whether the
same funder also funds the line's launch wallets or the 70adce63 operator wallets (searched in cache/fblocks.jsonl lines that carry
the funder's address)."""
import sys, os, pickle, json, subprocess
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
R = load_rows(); FP = fam_pools(R); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb")); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
F = pickle.load(open(os.path.join(OUT, "fleet_funding.pkl"), "rb"))
FUNDER = "0x4a6dbb33bc962c48db40e5eac91edf5ba316fe70"
buy_of = {}
for r in FP["tok:0f34e3b5"]:
    o = E[r["pool"]]
    for e in o["ev"]:
        t = T.get(e[-1])
        if t and e[0] == "s" and t["selector"] == "7ff36ab5" and t["calldata_len"] == 228:
            buy_of[t["from"]] = (e[1], int(t["value_wei"]) / 1e18)
d = []; ratio = []
for f in F["fund"]:
    if f[0] == "direct" and f[1] == FUNDER and f[2] in buy_of:
        d.append(buy_of[f[2]][0] - f[4]); ratio.append(buy_of[f[2]][1] / f[3])
d.sort(); ratio.sort()
print(f"funder {FUNDER}: fleet wallets funded (seen) {len(d)}; blocks funding -> buy p10/50/90 {d[len(d)//10]}/{d[len(d)//2]}/{d[9*len(d)//10]}; buy value / funding p10/50/90 {ratio[len(ratio)//10]:.3f}/{ratio[len(ratio)//2]:.3f}/{ratio[9*len(ratio)//10]:.3f}")
lines = subprocess.run(["grep", "-F", FUNDER[2:], os.path.join(CEN, "cache", "fblocks.jsonl")], capture_output=True, text=True).stdout.splitlines()
lw0 = {r["launch"]["from"] for r in FP["tok:0f34e3b5"]}; lw7 = {r["launch"]["from"] for r in FP["tok:70adce63"]}
op7 = {r["frb"]["eoa"] for r in FP["tok:70adce63"] if r["frb"]}
outs = Counter(); hits = Counter(); n = 0; ins = Counter()
for line in lines:
    b = json.loads(line)
    for tx in b["txs"]:
        if tx[1] == FUNDER:
            n += 1; to = tx[2]
            outs["0f34e3b5 fleet" if to in buy_of else "0f34e3b5 launch wallet" if to in lw0 else "70adce63 launch wallet" if to in lw7 else "70adce63 operator buyer" if to in op7 else "other"] += 1
        elif tx[2] == FUNDER and int(tx[3] or 0) > 0:
            ins[tx[1]] += 1
print(f"funder's txs in the cached blocks: {n}; recipients {outs.most_common()}; incoming transfers from {ins.most_common(3)}")
