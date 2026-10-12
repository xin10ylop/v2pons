"""Per-pool records (offline, from c01/c02/c03): launch, the trigger T (the first buy whose transaction goes to the operator's router), every
swap with its transaction (from, to, selector, size, offset), the first pull (ModifyLiquidity with negative liquidity), and a buyer class:
router (tx to 0xd6d35b56), ours (relay as Swap sender / our wallet), launcher (the pool's launch wallet or any C-1 launch wallet),
opEOA (an EOA seen calling the router, buying another way), recurring (an outside EOA buying in >= REC pools), oneoff (the rest).
Writes c05_pools.json and prints the buyer census."""
from common import *
import collections
REC = 5
X = json.load(open(J("c01_launches.json"))); byp = {x["pid"]: x for x in X}
head = json.load(open(J("c02_head.json")))["head"]
TX = {}
for l in open(J("c03_txs.jsonl")):
    t = json.loads(l); TX[t["hash"]] = t
ev = jl(J("c02_events.jsonl"))
launchers = {x["from"] for x in X}
routerEOA = {t["from"] for t in TX.values() if t["to"] == ROUTER}
P = {pid: {"pid": pid, "lb": x["lb"], "ts": x["ts"], "token": x["token"], "launcher": x["from"], "age": head - x["lb"], "sw": [], "ml": []} for pid, x in byp.items()}
for l in ev:
    pid = l["topics"][1]; p = P[pid]; bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); h = l["transactionHash"]; t = TX.get(h)
    if l["topics"][0] == T_SWAP:
        a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1))
        s = {"off": bn - p["lb"], "bn": bn, "li": li, "ti": int(l["transactionIndex"], 16), "buy": a0 < 0, "eth": abs(a0) / 1e18, "tok": abs(a1), "sqrtP": W(l["data"], 2),
             "liq": W(l["data"], 3), "sender": "0x" + l["topics"][2][-40:], "tx": h}
        if t: s.update({"from": t["from"], "to": t["to"], "sel": t["sel"], "n": t["n"], "nonce": t["nonce"], "value": t["value"]})
        p["sw"].append(s)
    else:
        d = sgn(W(l["data"], 2))
        m = {"off": bn - p["lb"], "bn": bn, "li": li, "liq": d, "tx": h, "sender": "0x" + l["topics"][2][-40:]}
        if t: m.update({"from": t["from"], "to": t["to"], "sel": t["sel"]})
        p["ml"].append(m)
for p in P.values():
    p["sw"].sort(key=lambda s: (s["bn"], s["li"])); p["ml"].sort(key=lambda m: (m["bn"], m["li"]))
    trig = next((s for s in p["sw"] if s["buy"] and s.get("to") == ROUTER), None)
    p["T"] = trig["off"] if trig else None; p["Tpos"] = (trig["bn"], trig["li"]) if trig else None; p["T_eth"] = trig["eth"] if trig else None
    p["T_sqrtP"] = trig["sqrtP"] if trig else None
    pl = next((m for m in p["ml"] if m["liq"] < 0), None)
    p["pull"] = pl["off"] if pl else None; p["pullpos"] = (pl["bn"], pl["li"]) if pl else None
    p["pull_tx"] = {k: pl.get(k) for k in ("tx", "from", "to", "sel", "sender")} if pl else None
    p["n_untx"] = sum(1 for s in p["sw"] if "from" not in s and s["off"] <= min(p["pull"] or 1 << 60, 3000))
# classes
def base(p, s):
    if "from" not in s: return "unknown"
    if s["to"] == ROUTER: return "router"
    if s["sender"] == RELAY or s["from"] == WALLET or s["to"] == RELAY: return "ours"
    if s["from"] in launchers: return "launcher"
    if s["from"] in routerEOA: return "opEOA"
    return "outside"
pools_of = collections.defaultdict(set)
for p in P.values():
    for s in p["sw"]:
        s["cls"] = base(p, s)
        if s["cls"] == "outside" and s["buy"]: pools_of[s["from"]].add(p["pid"])
recurring = {w for w, ps in pools_of.items() if len(ps) >= REC}
for p in P.values():
    for s in p["sw"]:
        if s["cls"] == "outside": s["cls"] = "recurring" if s["from"] in recurring else "oneoff"
json.dump({"pools": list(P.values()), "recurring": sorted(recurring), "routerEOA_n": len(routerEOA), "head": head}, open(J("c05_pools.json"), "w"))
pp = list(P.values())
print(f"pools {len(pp)}; with a router buy {sum(p['T'] is not None for p in pp)}; pulled {sum(p['pull'] is not None for p in pp)}; router EOAs {len(routerEOA)}; swaps without tx in the window {sum(p['n_untx'] for p in pp)}")
print("pull tx:", collections.Counter((p["pull_tx"] or {}).get("to") for p in pp).most_common(3), "pull sender == launcher:", sum(1 for p in pp if p["pull_tx"] and p["pull_tx"].get("from") == p["launcher"]), "of", sum(1 for p in pp if p["pull_tx"]))
# buyer census after T (before the pull), by class
cen = collections.defaultdict(lambda: [0, 0.0, set()])
for p in pp:
    if p["T"] is None: continue
    for s in p["sw"]:
        if not s["buy"] or (s["bn"], s["li"]) <= tuple(p["Tpos"]) or (p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"])): continue
        c = cen[s["cls"]]; c[0] += 1; c[1] += s["eth"]; c[2].add(p["pid"])
print("buys after T before the pull, by class: n / ETH / pools")
for k, (n, e, ps) in sorted(cen.items(), key=lambda kv: -kv[1][0]): print(f"  {k:10s} {n:6d} {e:9.4f} ETH {len(ps):4d} pools")
print("\nrecurring outside wallets (>= %d pools):" % REC)
fp = collections.defaultdict(lambda: collections.Counter()); sz = collections.defaultdict(list); offs = collections.defaultdict(list)
for p in pp:
    for s in p["sw"]:
        if s["buy"] and s["cls"] in ("recurring", "oneoff"):
            fp[s["from"]][f"{s['to'][:10]}:{s['sel']}:{s['n']}"] += 1; sz[s["from"]].append(s["eth"])
            if p["T"] is not None: offs[s["from"]].append(s["off"] - p["T"])
for w in sorted(recurring, key=lambda w: -len(pools_of[w])):
    print(f"  {w} pools {len(pools_of[w]):4d} buys {len(sz[w]):5d} size p50 {pct(sz[w], .5):.6f} max {max(sz[w]):.6f} offset-T p10/50/90 {pct(offs[w], .1)}/{pct(offs[w], .5)}/{pct(offs[w], .9)} via {fp[w].most_common(2)}")
oo = [w for w in pools_of if w not in recurring]
print(f"one-off outside wallets: {len(oo)}; their buys {sum(len(sz[w]) for w in oo)}; >= 0.001 ETH {sum(1 for w in oo for e in sz[w] if e >= 0.001)}")
