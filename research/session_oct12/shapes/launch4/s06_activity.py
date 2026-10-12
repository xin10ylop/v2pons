"""Lifetime activity per shape (offline: s04_pools.json + s05 swaps and txs): the shape's core (S1 = the 4,324-byte hooked launches only),
every swap from the launch to the head with its transaction, per-pool first outside buy, buyers by EOA and by target across pools, wallet
P&L in the quote (realized + held at the pool's last price), price multiple vs the launch price. Writes s06_pools.json; prints s06_activity.out."""
from common import *
import collections
D = json.load(open(J("s04_pools.json"))); head = json.load(open(J("s05_head.json")))["head"]
TX = {t["hash"]: t for t in jl(C("s03_tx_cache.jsonl")) + jl(C("s05_tx_cache.jsonl"))}
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"     # the dust sentinel (2e-6 ETH at +2..4 in every pool, REPORT_T3/C1R)
def core(p):
    if p["shape"] == "S1": return p["n"] == 4324 and p["hook"].endswith("44a9a544")
    return True
P = [p for p in D["pools"] if core(p)]
byp = {p["pid"]: p for p in P}
f_of = {}
for p in P:
    sw = [w for w in p["sw"] if w["eth"] is not None and w["q"]]
    f_of[p["pid"]] = (sw[0]["eth"] / sw[0]["q"]) if sw else {"ETH": 1e-18, "WETH": 1e-18, "USDG": 1 / 2570 / 1e6}.get(p["qname"])
for l in jl(C("s05_sw_cache.jsonl")):
    p = byp.get(l["topics"][1])
    if not p: continue
    bn = int(l["blockNumber"], 16)
    if bn <= p["lb"] + 600: continue
    t = TX.get(l["transactionHash"], {}); a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1)); aq, ac = (a0, a1) if p["qs"] == 0 else (a1, a0)
    f = f_of[p["pid"]]
    p["sw"].append({"off": bn - p["lb"], "bn": bn, "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "from": t.get("from"),
                    "to": t.get("to"), "sel": t.get("sel"), "tvalue": int(t["value"], 16) / 1e18 if t else None, "inlaunch": False, "buy": aq < 0, "q": abs(aq), "c": abs(ac),
                    "eth": abs(aq) * f if f else None, "sqrtP": W(l["data"], 2), "tick": sgn(W(l["data"], 4)), "swfee": W(l["data"], 5)})
def price(p, sp):   # quote per coin, relative units
    x = (sp / 2 ** 96) ** 2
    return 1 / x if p["qs"] == 0 else x
for p in P:
    p["sw"].sort(key=lambda w: (w["bn"], w["li"]))
    p0 = price(p, p["sqrtP0"])
    for w in p["sw"]: w["mult"] = price(p, w["sqrtP"]) / p0
    out = [w for w in p["sw"] if not w["inlaunch"] and w["from"] != SENT]
    p["n_out"] = len(out)
    fb = next((w for w in out if w["buy"] and (w["eth"] or 0) >= 1e-4), None)
    p["first_buy"] = {k: fb[k] for k in ("off", "eth", "from", "to", "sel", "mult")} if fb else None
    p["max_mult"] = max([w["mult"] for w in p["sw"]] + [1.0]); p["last_mult"] = p["sw"][-1]["mult"] if p["sw"] else 1.0
json.dump({"head": head, "pools": P}, open(J("s06_pools.json"), "w"))
for s in ("S1", "S2", "S3", "S4"):
    pp = [p for p in P if p["shape"] == s]
    act = [p for p in pp if p["n_out"]]
    fb = [p for p in pp if p["first_buy"]]
    print(f"===== {s}: {len(pp)} core pools; with any non-sentinel swap after the launch tx (to the head): {len(act)}; with a buy >= 0.0001 ETH-eq: {len(fb)}")
    print(f"  pool age at the head: p10/50/90 {pct([p['age'] for p in pp], .1)}/{pct([p['age'] for p in pp], .5)}/{pct([p['age'] for p in pp], .9)} blocks")
    print(f"  first buy (>= 0.0001) offsets: {sorted(p['first_buy']['off'] for p in fb)[:40]}")
    print(f"  first buy within +600: {sum(1 for p in fb if p['first_buy']['off'] <= 600)}; sizes ETH-eq {sorted(round(p['first_buy']['eth'], 4) for p in fb)[:40]}")
    print(f"  max price multiple vs launch: p50 {pct([p['max_mult'] for p in pp], .5):.3f} p90 {pct([p['max_mult'] for p in pp], .9):.3f} max {max(p['max_mult'] for p in pp):.3f}; "
          f">= 1.5x: {sum(1 for p in pp if p['max_mult'] >= 1.5)}; >= 2x: {sum(1 for p in pp if p['max_mult'] >= 2)}")
    E = collections.defaultdict(lambda: {"pools": set(), "buys": 0, "sells": 0, "in": 0.0, "out": 0.0, "big": 0, "offs": []}); T = collections.defaultdict(lambda: [set(), 0, 0.0])
    for p in pp:
        for w in p["sw"]:
            if w["inlaunch"]: continue
            e = E[w["from"]]; e["pools"].add(p["pid"])
            if w["buy"]:
                e["buys"] += 1; e["in"] += w["eth"] or 0; e["offs"].append(w["off"]); e["big"] += (w["eth"] or 0) >= 0.05
                t = T[(w["to"], w["sel"])]; t[0].add(p["pid"]); t[1] += 1; t[2] += w["eth"] or 0
            else: e["sells"] += 1; e["out"] += w["eth"] or 0
    print(f"  swapping EOAs {len(E)}; in >= 2 pools: {sum(1 for e in E.values() if len(e['pools']) >= 2)}; in >= 3 pools: {sum(1 for e in E.values() if len(e['pools']) >= 3)}")
    for w, e in sorted(E.items(), key=lambda kv: (-len(kv[1]["pools"]), -kv[1]["in"]))[:10]:
        print(f"    {w} pools {len(e['pools']):3d} buys {e['buys']:3d} in {e['in']:.4f} sells {e['sells']:3d} out {e['out']:.4f} buys>=0.05 {e['big']} offsets p10/50/90 {pct(e['offs'], .1)}/{pct(e['offs'], .5)}/{pct(e['offs'], .9)}")
    print("  buy targets:", [(k[0][:10] if k[0] else None, k[1], len(v[0]), v[1], round(v[2], 4)) for k, v in sorted(T.items(), key=lambda kv: -len(kv[1][0]))[:6]])
    big = [(p["pid"][:10], w["off"], round(w["eth"], 4), w["from"][:10]) for p in pp for w in p["sw"] if w["buy"] and not w["inlaunch"] and (w["eth"] or 0) >= 0.05]
    print(f"  buys >= 0.05 ETH-eq (any time): {len(big)} {big[:20]}")
