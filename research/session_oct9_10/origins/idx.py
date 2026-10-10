"""Index of every value>0 tx (plain or call) in the shared block cache ops/lch/bc + all txs sent by crowd A/B wallets.
Output vt.pkl: list of (bn, ts, hash, from, to, wei, nonce, sel) and covered block ranges."""
import json, os, glob, pickle, sys
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
b = json.load(open(D + "ops/b_list.json")); CA = set(b["A"]); CB = set(b["B"])
out = {}; cov = set()
files = glob.glob(D + "ops/lch/bc/*.json")
for i, f in enumerate(files):
    try: d = json.load(open(f))
    except Exception as e: print("skip", f, e); continue
    for k, (ts, tl) in d.items():
        bn = int(k); cov.add(bn)
        for t in tl:
            h, fr, to, v, nonce, sel = t[0], t[1], t[2], int(t[3]), t[4], t[5]
            if v > 0 or fr in CA or fr in CB:
                out[h] = (bn, ts, h, fr, to, v, nonce, sel)
    if i % 100 == 0: print(i, len(files), len(out), flush=True)
# merge money/blocks.pkl (no timestamps: estimate from block number, 0.1011 s/block anchored at 83086638 = 1791439148)
try:
    BL = pickle.load(open(D + "money/blocks.pkl", "rb"))
    for bn, tl in BL.items():
        cov.add(bn); ts = int(1791439148 + (bn - 83086638) * 0.1011)
        for (h, fr, to, v, nonce, sel) in tl:
            if h not in out and (v > 0 or fr in CA or fr in CB): out[h] = (bn, ts, h, fr, to, v, nonce, sel)
except Exception as e: print("blocks.pkl skip", e)
cov = sorted(cov); rng = []
for n in cov:
    if rng and n == rng[-1][1] + 1: rng[-1][1] = n
    else: rng.append([n, n])
pickle.dump({"tx": sorted(out.values()), "ranges": rng}, open(D + "origins/vt.pkl", "wb"))
print(len(out), "txs;", len(rng), "ranges", sum(b - a + 1 for a, b in rng), "blocks")
