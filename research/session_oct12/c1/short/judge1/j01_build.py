"""Judge 1, build: the analyst's 208 pools (s02_pools.json, DATA only, to 14:14 UTC) with its two 14:00-shape pools replaced, plus the 10 C-1
launches since (j00), rebuilt here with the same fields (c05/s02 logic: swap sizes, fee field, buyer classes router / ours / launcher / opEOA /
recurring / oneoff). Each pool also gets mint_liq (the launch ModifyLiquidity) and shape ("line" = the family's sqrtP and L, "1400" = the
14:00 shape). Writes j01_pools.json."""
from jc import *
import collections
D = json.load(open(SH("s02_pools.json"))); J0 = json.load(open(JD("j00_launches.json"))); NEW = J0["launches"]; M = json.load(open(JD("j00_meta.json")))
newids = {x["pid"] for x in NEW}
old = [p for p in D["pools"] if p["pid"] not in newids]
TX = {}
for fn in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl"), JD("j00_txs.jsonl")):
    for l in open(fn):
        t = json.loads(l); TX[t["hash"]] = t
X0 = json.load(open(J("c01_launches.json"))) + json.load(open(SH("s01_launches_new.json")))
launchers = {x["from"] for x in X0} | {x["from"] for x in NEW}
routerEOA = {t["from"] for t in TX.values() if t["to"] == ROUTER}
recurring = set(D["recurring"])
ev = jl(JD("j00_events.jsonl"))
P = {x["pid"]: {"pid": x["pid"], "lb": x["lb"], "ts": x["ts"], "token": x["token"], "launcher": x["from"], "launch_sqrtP": x["sqrtP"], "age": M["head"] - x["lb"], "sw": [], "ml": []} for x in NEW}
for l in ev:
    pid = l["topics"][1]; p = P[pid]; bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); h = l["transactionHash"]; t = TX.get(h)
    if l["topics"][0] == T_SWAP:
        a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1))
        s = {"off": bn - p["lb"], "bn": bn, "li": li, "ti": int(l["transactionIndex"], 16), "buy": a0 < 0, "eth": abs(a0) / 1e18, "eth_wei": abs(a0), "tok": abs(a1), "fee": W(l["data"], 5),
             "sqrtP": W(l["data"], 2), "liq": W(l["data"], 3), "sender": "0x" + l["topics"][2][-40:], "tx": h}
        if t: s.update({"from": t["from"], "to": t["to"], "sel": t["sel"], "n": t["n"], "nonce": t["nonce"], "value": t["value"]})
        p["sw"].append(s)
    else:
        d = sgn(W(l["data"], 2))
        m = {"off": bn - p["lb"], "bn": bn, "li": li, "liq": d, "tx": h, "sender": "0x" + l["topics"][2][-40:]}
        if t: m.update({"from": t["from"], "to": t["to"], "sel": t["sel"]})
        p["ml"].append(m)
def base(s):
    if "from" not in s: return "unknown"
    if s["to"] == ROUTER: return "router"
    if s["sender"] == RELAY or s["from"] == WALLET or s["to"] == RELAY: return "ours"
    if s["from"] in launchers: return "launcher"
    if s["from"] in routerEOA: return "opEOA"
    return "recurring" if s["from"] in recurring else "oneoff"
for p in P.values():
    p["sw"].sort(key=lambda s: (s["bn"], s["li"])); p["ml"].sort(key=lambda m: (m["bn"], m["li"]))
    for s in p["sw"]: s["cls"] = base(s)
    pl = next((m for m in p["ml"] if m["liq"] < 0), None)
    p["pull"] = pl["off"] if pl else None; p["pullpos"] = (pl["bn"], pl["li"]) if pl else None
    p["pull_tx"] = {k: pl.get(k) for k in ("tx", "from", "to", "sel", "sender")} if pl else None
    p["n_untx"] = sum(1 for s in p["sw"] if "from" not in s and s["off"] <= min(p["pull"] or 1 << 60, 1500))
pools = old + list(P.values())
for p in pools:
    p["mint_liq"] = next((m["liq"] for m in p["ml"] if m["liq"] > 0 and m["off"] == 0), None)
    p["shape"] = "line" if (p["launch_sqrtP"], p["mint_liq"]) == (SQRTP, LIQ) else "1400" if (p["launch_sqrtP"], p["mint_liq"]) == (835109957917073511657837871095390, 94871533698238694366969) else "other"
    p["new"] = p["pid"] in newids
print(f"pools {len(pools)} (old {len(old)}, rebuilt/new {len(P)}); shapes {collections.Counter(p['shape'] for p in pools)}; head {M['head']} {utc(M['head_ts'])}")
for p in sorted(P.values(), key=lambda p: p["lb"]):
    print(f"  {utc(p['ts'])} {p['pid'][:10]} shape {next(q['shape'] for q in pools if q['pid'] == p['pid'])} launcher {p['launcher'][:10]} swaps {len(p['sw'])} "
          f"router buys {sum(1 for s in p['sw'] if s['buy'] and s['cls'] == 'router')} pull {p['pull']} by {(p['pull_tx'] or {}).get('from', '-')[:10]} via {(p['pull_tx'] or {}).get('to', '-')[:10]} untx {p['n_untx']}")
json.dump({"pools": pools, "head": M["head"], "head_ts": M["head_ts"], "recurring": sorted(recurring)}, open(JD("j01_pools.json"), "w"))
