"""Judge 2, step 5 (offline, j04 caches): the 14:00 shape against the old shape on the same afternoon. Is it the same operator and router,
and do its pools behave the same (router buying, outside holders, pull timing), and what would the engine-exact c1 exits have made on it
(as if the family took the new fingerprint: with "pin" true the engine does not arm it at all, arm_front line 1231)?"""
from j02_sim import *
L4 = json.load(open(JD("j04_launches.json"))); M4 = json.load(open(JD("j04_meta.json"))); HEAD4 = M4["head"]
for l in open(JD("j04_txs.jsonl")):
    t = json.loads(l); TX[t["hash"]] = t
REC = set(D["recurring"])
EV = collections.defaultdict(list)
for l in open(JD("j04_events.jsonl")):
    l = json.loads(l); EV[l["topics"][1]].append(l)
s24 = lambda x: x - (1 << 24) if x >= (1 << 23) else x
NEW_SP = 835109957917073511657837871095390


def build(x):
    """a pool record in s02's form from the j04 logs"""
    ml, sw = [], []
    for l in EV[x["pid"]]:
        bn = int(l["blockNumber"], 16); li = int(l["logIndex"], 16); ti = int(l["transactionIndex"], 16); h = l["transactionHash"]
        t = TX.get(h, {})
        if l["topics"][0] == T_ML:
            ml.append({"off": bn - x["lb"], "bn": bn, "li": li, "liq": sgn(W(l["data"], 2)), "tx": h, "from": t.get("from"), "to": t.get("to")}); continue
        a0, a1 = sgn(W(l["data"], 0)), sgn(W(l["data"], 1)); buy = a0 < 0
        frm = t.get("from"); to = t.get("to")
        cls = "router" if to == ROUTER else "ours" if frm == WALLET else ("recurring" if frm in REC else "oneoff") if frm else "unknown"
        sw.append({"off": bn - x["lb"], "bn": bn, "li": li, "ti": ti, "buy": buy, "eth": abs(a0) / 1e18, "eth_wei": -a0 if buy else a0, "tok": -a1 if not buy else a1,
                   "fee": s24(W(l["data"], 5)) if W(l["data"], 5) < (1 << 24) else W(l["data"], 5), "sqrtP": W(l["data"], 2), "liq": W(l["data"], 3), "tx": h, "from": frm, "to": to,
                   "sel": t.get("sel"), "value": t.get("value", 0), "cls": cls})
    neg = [m for m in ml if m["liq"] < 0]
    pull = min(neg, key=lambda m: (m["bn"], m["li"])) if neg else None
    return {"pid": x["pid"], "lb": x["lb"], "ts": x["ts"], "token": x["token"], "launch_sqrtP": x["sqrtP"], "ml": ml, "sw": sw, "from": x["from"],
            "pull": pull["off"] if pull else None, "pullpos": [pull["bn"], pull["li"]] if pull else None, "pull_by": pull["from"] if pull else None,
            "L": next((m["liq"] for m in ml if m["liq"] > 0), None)}


def engine_copy_L(p, L):
    cp = float(p["launch_sqrtP"]); done = set()
    for k, s in enumerate(p["sw"]):
        a = seen(p, s)
        if a is None or a[1] is None or s["tx"] in done: continue
        done.add(s["tx"]); cp = v4math.sqrt_after_buy(cp, L, net(a[1], FEE))
        if a[0] in ("router", "router?") and a[1] >= MIN_TRIG: return (k, s, cp)
    return None


def sim_L(p, trig, dB, lag, L, stake=STAKE):
    """j02's simulate with the pool's own launch liquidity in the engine's copy (the engine copies it from the launch calldata)"""
    import j02_sim as m
    old = m.LIQ; m.LIQ = L
    try:
        return m.simulate(p, trig, dB, lag, stake)
    finally:
        m.LIQ = old


if __name__ == "__main__":
    pools = [build(x) for x in L4]
    print(f"launches since 13:30 UTC: {len(pools)} (new shape {sum(p['launch_sqrtP'] == NEW_SP for p in pools)}); head {HEAD4} {utc(M4['head_ts'])}")
    print("\n(1) operator: launch wallet, its nonce at the launch, the launch L, who pulled, through what; router buys (to 0xd6d35b56)")
    allrouter = collections.Counter()
    for p in pools:
        shape = "NEW" if p["launch_sqrtP"] == NEW_SP else "old"
        trig = engine_copy_L(p, p["L"])
        T = trig[1]["off"] if trig else None
        rb = [s for s in p["sw"] if s["cls"] == "router" and s["buy"]]; rs = [s for s in p["sw"] if s["cls"] == "router" and not s["buy"]]
        for s in rb: allrouter[s["from"]] += 1
        lt = TX.get(next((m["tx"] for m in p["ml"] if m["liq"] > 0), ""), {})
        r60 = sum(s["eth"] for s in rb if T is not None and s["off"] <= T + 60)
        outs = [(s["off"] - (T or 0), s["cls"], s["from"][:10], round(s["eth"], 5), "sold" if any((not y["buy"]) and y["from"] == s["from"] for y in p["sw"] if (y["bn"], y["li"]) > (s["bn"], s["li"])) else "held")
                for s in p["sw"] if s["buy"] and s["cls"] in ("recurring", "oneoff") and s["eth"] >= 0.0005 and (p["pull"] is None or s["off"] <= p["pull"])]
        print(f"  {utc(p['ts'])} {p['pid'][:10]} {shape} L {p['L']} launch wallet {p['from'][:10]} (nonce {lt.get('nonce')}); T "
              + (f"+{T} ({trig[1]['eth_wei'] / 1e18:.4f})" if trig else "none") + f"; router buys {len(rb)} ({sum(s['eth'] for s in rb):.3f} ETH), sells {len(rs)}; by T+60 {r60:.3f} ETH; "
              + f"pull +{p['pull']}" + (f" (T+{p['pull'] - T})" if p["pull"] is not None and T is not None else "") + (f" by {'the launch wallet' if p['pull_by'] == p['from'] else p['pull_by']}" if p["pull"] is not None else " (live)")
              + f"; outside buys >= 0.0005 (T+off, class, from, ETH, held/sold): {outs}")
    old_eoas = set()
    for p in P:
        for s in p["sw"]:
            if s.get("to") == ROUTER: old_eoas.add(s.get("from"))
    newp = [p for p in pools if p["launch_sqrtP"] == NEW_SP]
    ne = {s["from"] for p in newp for s in p["sw"] if s["cls"] == "router"}
    print(f"\n  router EOAs in the new-shape pools: {len(ne)}, of them seen in the 208 cached pools before 14:14: {len(ne & old_eoas)}")
    dust = collections.Counter(s["from"][:10] for p in newp for s in p["sw"] if s["cls"] in ("recurring", "oneoff") and s["buy"])
    print(f"  outside buyers in the new-shape pools: {dict(dust)}")
    # (2) the engine-exact exits on both shapes since 13:30 (the new shape as if armed)
    print("\n(2) engine-exact c1 exits since 13:30 (buy T+2, lag 2; the new shape as if armed with its own price and L): gross per exit, pull from our buy")
    for p in pools:
        shape = "NEW" if p["launch_sqrtP"] == NEW_SP else "old"
        trig = engine_copy_L(p, p["L"])
        if trig is None: print(f"  {p['pid'][:10]} {shape}: no trigger"); continue
        if HEAD4 - p["lb"] < trig[1]["off"] + 75: print(f"  {p['pid'][:10]} {shape}: T+{trig[1]['off']}, too young"); continue
        x = sim_L(p, trig, 2, 2, p["L"])
        if not x["fill"]: print(f"  {p['pid'][:10]} {shape} T+{trig[1]['off']}: REVERT ({x['why']} {x.get('short', 0):+.2%}); pull T+{(p['pull'] - trig[1]['off']) if p['pull'] is not None else None}"); continue
        gs = " ".join(f"{e} {x['res'][e][0] * 100:+.1f}" for e in ("hold 20", "hold 25", "hold 30", "hold 60", "tp 4% cap 30"))
        print(f"  {p['pid'][:10]} {shape} T+{trig[1]['off']}: {gs} | pull buy+{x['pull_after_buy']}")
