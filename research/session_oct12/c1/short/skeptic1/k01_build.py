"""Skeptic 1 (short exit), my own pool records straight from the raw caches (offline; no RPC).
Inputs (read only): ../../c01_launches.json, ../s01_launches_new.json (launches); ../../c02_events.jsonl, ../s01_events_new.jsonl
(Swap + ModifyLiquidity logs); ../../c03_txs.jsonl, ../s01_txs_new.jsonl (the attributed transactions); ../../c02_relay_swaps.json.
Classes (my own, not c05's): router = tx to 0xd6d35b56; ours = Swap sender is our relay or tx from our wallet; launcher = tx from any
C-1 launch wallet; opEOA = an EOA that ever called the router; out = everyone else. T = the first BUY whose tx goes to the router
(also the engine's min_eth 0.005 / max_blocks 400 trigger, recorded apart as Teng). Pull = the first ModifyLiquidity with negative delta.
Writes k01_pools.json."""
import json, os, sys, collections
H = os.path.dirname(os.path.abspath(__file__)); SH = os.path.dirname(H); C1 = os.path.dirname(SH)
ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
sg = lambda x: x - (1 << 256) if x >= (1 << 255) else x
L0 = {}
for f in (os.path.join(C1, "c01_launches.json"), os.path.join(SH, "s01_launches_new.json")):
    for x in json.load(open(f)): L0[x["pid"]] = x
TX = {}
for f in (os.path.join(C1, "c03_txs.jsonl"), os.path.join(SH, "s01_txs_new.jsonl")):
    for l in open(f):
        t = json.loads(l); TX[t["hash"]] = t
seen = set(); EV = collections.defaultdict(list)
for f in (os.path.join(C1, "c02_events.jsonl"), os.path.join(SH, "s01_events_new.jsonl")):
    for l in open(f):
        e = json.loads(l); k = (e["transactionHash"], int(e["logIndex"], 16))
        if k in seen: continue
        seen.add(k); EV[e["topics"][1]].append(e)
launchers = {x["from"] for x in L0.values()}
routerEOA = {t["from"] for t in TX.values() if t.get("to") == ROUTER}
pools = []
for pid, x in L0.items():
    sw, ml = [], []
    for e in sorted(EV.get(pid, []), key=lambda e: (int(e["blockNumber"], 16), int(e["logIndex"], 16))):
        bn = int(e["blockNumber"], 16); li = int(e["logIndex"], 16); t = TX.get(e["transactionHash"]); d = e["data"]
        if e["topics"][0] == T_SWAP:
            a0, a1 = sg(W(d, 0)), sg(W(d, 1)); sender = "0x" + e["topics"][2][-40:]
            s = {"bn": bn, "li": li, "off": bn - x["lb"], "buy": a0 < 0, "eth_wei": abs(a0), "tok": abs(a1), "sp": W(d, 2), "liq": W(d, 3),
                 "fee": W(d, 5), "tx": e["transactionHash"], "sender": sender, "from": t["from"] if t else None, "to": t["to"] if t else None}
            if t is None: c = "unknown"
            elif t["to"] == ROUTER: c = "router"
            elif sender == RELAY or t["from"] == WALLET or t["to"] == RELAY: c = "ours"
            elif t["from"] in launchers: c = "launcher"
            elif t["from"] in routerEOA: c = "opEOA"
            else: c = "out"
            s["c"] = c; sw.append(s)
        elif e["topics"][0] == T_ML:
            ml.append({"bn": bn, "li": li, "off": bn - x["lb"], "d": sg(W(d, 2)), "lo": sg(W(d, 0)), "hi": sg(W(d, 1)),
                       "from": t["from"] if t else None})
    trig = next((s for s in sw if s["buy"] and s["c"] == "router"), None)
    teng = next((s for s in sw if s["buy"] and s["c"] == "router" and s["eth_wei"] >= 5 * 10 ** 15 and s["off"] <= 400), None)
    pull = next((m for m in ml if m["d"] < 0), None)
    pools.append({"pid": pid, "lb": x["lb"], "ts": x["ts"], "launcher": x["from"], "sqrtP0": x["sqrtP"], "sw": sw, "ml": ml,
                  "T": trig["off"] if trig else None, "Tpos": [trig["bn"], trig["li"]] if trig else None,
                  "Teng": teng["off"] if teng else None,
                  "pull": pull["off"] if pull else None, "pullpos": [pull["bn"], pull["li"]] if pull else None,
                  "pull_from_launcher": (pull["from"] == x["from"]) if pull else None, "pull_d": pull["d"] if pull else None})
head = max(int(e["blockNumber"], 16) for v in EV.values() for e in v)
json.dump({"pools": pools, "head": head}, open(os.path.join(H, "k01_pools.json"), "w"))
print(f"pools {len(pools)} with T {sum(p['T'] is not None for p in pools)} pulled {sum(p['pull'] is not None for p in pools)} head {head}")
print("unknown-class swaps within launch..min(pull, launch+3000):",
      sum(1 for p in pools for s in p["sw"] if s["c"] == "unknown" and s["off"] <= min(p["pull"] or 10 ** 9, 3000)))
print("T != Teng (engine trigger differs):", [(p["pid"][:10], p["T"], p["Teng"]) for p in pools if p["T"] != p["Teng"]])
print("pull by launch wallet:", collections.Counter(p["pull_from_launcher"] for p in pools))
