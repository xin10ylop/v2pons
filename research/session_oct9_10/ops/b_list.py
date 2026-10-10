"""Reproduce crowd families A/B from load_all + classify; list B wallets, the B launches, per-launch group flows."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
L = collections.defaultdict(set); N = collections.defaultdict(list)
for p in pools:
    for x in p["sw"]:
        if x["from"] in cw: L[x["from"]].add(p["pid"]); N[x["from"]].append(x["nonce"])
w4 = next(w for w in cw if w.startswith("0x4c45af68")); B7 = L[w4]
SPECK = next((w for w in cw if w.startswith("0xb4d43149")), None)
fam = {}
for w in cw:
    if w == SPECK: fam[w] = "speck"
    elif L[w] <= B7 and len(L[w]) >= 3: fam[w] = "B"
    elif min(N[w]) <= 3 and len(L[w]) <= 2: fam[w] = "fresh"
    elif len(L[w]) >= 20: fam[w] = "A"
    else: fam[w] = "other_fp"
print(collections.Counter(fam.values()))
pid2 = {p["pid"]: p for p in pools}
print("B7 launches:")
for pid in sorted(B7, key=lambda k: pid2[k]["b0"]):
    p = pid2[pid]; print(utc(p["ts"]), pid[:10], p["kind"], p["fee"], p["b0"], "dep", p["deployer"], "pull", p["pull"]["bn"] if p["pull"] else None, p["m"].get("token"))
B = sorted(w for w in cw if fam[w] == "B")
A = sorted(w for w in cw if fam[w] == "A")
out = {"B": {}, "A": A, "B7": sorted(B7), "fam": fam}
for w in B:
    sws = [(pid2[pid], x) for pid in L[w] for x in pid2[pid]["sw"] if x["from"] == w]
    buys = [x for p, x in sws if x["a0"] < 0]; sells = [x for p, x in sws if x["a0"] > 0]
    ns = sorted(x["nonce"] for p, x in sws)
    out["B"][w] = {"launches": len(L[w]), "buys": len(buys), "sells": len(sells), "eth_in": sum(-x["a0"] for x in buys)/1e18, "eth_out": sum(x["a0"] for x in sells)/1e18,
                   "nonce_min": ns[0], "nonce_max": ns[-1], "first_bn": min(x["bn"] for p, x in sws), "last_bn": max(x["bn"] for p, x in sws)}
    print(w, out["B"][w])
# any other wallets (not crowd fp) on B7 launches
json.dump(out, open("b_list.json", "w"), indent=1)
