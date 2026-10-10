import sys, json, collections, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
utc = lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%m-%d %H:%M:%S")
for k in K:
    print(k, [(utc(P[x]["launch_ts"]), P[x]["launch_from"][:10], P[x]["launch_nonce"]) for x in F[k]["pids"]])
fam1 = F[K[0]]["pids"]
L1 = set(P[x]["liq_launch"] for x in fam1)
print("\n== pools with fam1 launch liquidity or value 1.8/2.0 with fee 500, or fee 500 ts 10")
for p in P.values():
    if p["liq_launch"] in L1 or (p["fee"] == 500 and p["tick_spacing"] == 10) or (p["launch_value_eth"] in (1.8, 2.0)):
        print(" ", p["pid"][:12], p["family"][:60], p["fee"], p["tick_spacing"], p["launch_value_eth"], p["launch_from"][:10], p["launch_nonce"], utc(p["launch_ts"]), p["n_buys"], p["first_pull_rel"], p["known"])
# fresh-wallet UR len-1284 buyers
print("\n== swaps whose tx: to UR, calldata 1284, nonce 0, by pool family")
c = collections.Counter(); ex = {}
for t in T.values():
    if t["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904" and t["calldata_len"] == 1284 and t["nonce"] == 0 and "swap" in t.get("kind", []):
        for pid, kind, rk in t["refs"]:
            if kind == "swap": c[P[pid]["family"]] += 1; ex[P[pid]["family"]] = pid
for f, n in c.most_common(20): print(" ", n, f, F[f]["count"], F[f]["known"])
print("\n== deployer 0x0587d47d and router 0x75379d5d")
D3 = "0x0587d47d149b2a0fbcd570b2cf8f551d26a7a703"
for p in P.values():
    if p["launch_from"] == D3: print(" ", p["pid"][:12], p["family"], p["launch_nonce"], utc(p["launch_ts"]), p["n_buys"], p["first_pull_rel"])
c = collections.Counter(); pools75 = collections.Counter()
for t in T.values():
    if t["to"] == "0x75379d5d2ea4c98aeaa57f32e233707550ab03f0":
        for pid, kind, rk in t["refs"]:
            if kind == "swap": c[P[pid]["family"]] += 1; pools75[pid] += 1
print(" router 0x75379d5d swaps (first-8) in", len(pools75), "pools; families:")
for f, n in c.most_common(15): print("   ", n, f, F[f]["count"], F[f]["known"])
print("\n== deployers of fam 2 and 4")
for d in ("0x909a0af40a3577f60bb3b0d6bd38fe2d8adfed54", "0x5dc9708f972a56d43620cc61f8236c5177270ce5", "0xa1e4bca023d741bd8d8609875ceef2abd8d755a3", "0x743508ffae72e5711c1f9d9765ca32794b6e43b9"):
    ps = [p for p in P.values() if p["launch_from"] == d]
    print(" ", d, len(ps), collections.Counter((p["fee"], p["tick_spacing"], p["calldata_len"]) for p in ps).most_common(8), "pulled", sum(1 for p in ps if p["first_pull_rel"] is not None), "with buys", sum(1 for p in ps if p["n_buys"]))
