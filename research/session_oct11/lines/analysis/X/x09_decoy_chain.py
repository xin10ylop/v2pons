"""The funding graph of the fresh wallets that buy through the operator-side routers 0x65050a9b (D65) and 0xfd1b271f (DFD): each one
(x08) buys (nonce 0), approves, sells, then sends its whole balance on in a plain transfer (the last nonce). For every fresh wallet that
sold within launch + 400, read the blocks from its sell to sell + 12 and find that transfer: the destination (the next wallet in the
chain, or a collector) and the amount. -> x09_chain.json; prints the chains, their roots and their ends."""
import json, pickle, collections
from rpc import batch, STATS
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
fresh = {}
for p in pools:
    for s in p["sw"]:
        if s["buy"] and s["to"] in (R65, RFD) and s["nonce"] is not None and s["nonce"] <= 1 and s["eoa"] not in fresh:
            sell = next((x for x in p["sw"] if not x["buy"] and x["eoa"] == s["eoa"]), None)
            fresh[s["eoa"]] = {"w": s["eoa"], "router": s["to"][:10], "buy_bn": s["bn"], "q": s["q"] / 1e18, "pid": p["pid"], "line": p["line"], "ts": p["ts"],
                               "sell_bn": sell["bn"] if sell else None, "sell_eth": sell["q"] / 1e18 if sell else None}
print("fresh wallets via D65/DFD:", len(fresh), collections.Counter((f["router"], f["sell_bn"] is not None) for f in fresh.values()))
try: done = {x["w"]: x for x in json.load(open("x09_chain.json"))}
except Exception: done = {}
todo = [f for f in fresh.values() if f["sell_bn"] and f["w"] not in done]
for i in range(0, len(todo), 2):
    grp = todo[i:i + 2]; bl = sorted(set(b for f in grp for b in range(f["sell_bn"], f["sell_bn"] + 13)))
    blks = dict(zip(bl, batch("eth_getBlockByNumber", [[hex(b), True] for b in bl], 26)))
    for f in grp:
        f["out"] = []
        for b in range(f["sell_bn"], f["sell_bn"] + 13):
            for t in (blks.get(b) or {}).get("transactions", []):
                if t["from"].lower() == f["w"] and (t.get("input") or "0x") == "0x":
                    f["out"].append({"bn": b, "to": (t.get("to") or "").lower(), "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16)})
        done[f["w"]] = f
    if i % 40 == 0:
        json.dump(list(done.values()), open("x09_chain.json", "w")); print(f"  {i}/{len(todo)}", STATS, flush=True)
for f in fresh.values():
    if f["w"] not in done: done[f["w"]] = f
json.dump(list(done.values()), open("x09_chain.json", "w"))
nxt = {w: (f.get("out") or [{}])[0].get("to") for w, f in done.items()}
prev = collections.defaultdict(list)
for w, n in nxt.items():
    if n: prev[n].append(w)
print("sweeps found:", sum(1 for v in nxt.values() if v), "of", len(done))
dest = collections.Counter(n if n not in fresh else "another fresh wallet" for n in nxt.values() if n)
print("sweep destinations:", dest.most_common(12))
roots = [w for w in fresh if not prev.get(w)]
print("fresh wallets nobody in the set funded (chain roots):", len(roots))
# chains
seen = set(); chains = []
for r in sorted(roots, key=lambda w: fresh[w]["buy_bn"]):
    ch = [r]; seen.add(r)
    while nxt.get(ch[-1]) in fresh and nxt[ch[-1]] not in seen:
        ch.append(nxt[ch[-1]]); seen.add(ch[-1])
    chains.append(ch)
print("chains:", len(chains), "lengths:", sorted((len(c) for c in chains), reverse=True)[:15])
for c in sorted(chains, key=len, reverse=True)[:12]:
    a, z = fresh[c[0]], fresh[c[-1]]
    print(f"  len {len(c):3d} {utc(a['ts'])} .. {utc(z['ts'])} router {a['router']} sizes {collections.Counter(round(fresh[w]['q'], 4) for w in c).most_common(2)} root {c[0]} end -> {nxt.get(c[-1])}")
