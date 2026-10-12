"""Per-pool records (offline, from s01/s03 caches): coin and quote, every Swap in [launch, launch + 600] with its transaction (from, to, selector,
bytes, value) and ETH-equivalent size, every ModifyLiquidity to the head, the first pull (ModifyLiquidity with negative liquidity). Writes
s04_pools.json and prints a census per shape (s04_build.out). Swap amounts are the swapper's deltas: negative = paid into the pool.
ETH equivalents: ETH/WETH 1; USDG (6 decimals) at 1/2570 ETH (census convention); SPCX at the rate in s04_rates.json if present; else None."""
from common import *
import collections
WIN = 600
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"; SPCX = "0x4a0e65a3eccec6dbe60ae065f2e7bb85fae35eea"; Z = "0x" + "0" * 40
rates = json.load(open(J("s04_rates.json"))) if os.path.exists(J("s04_rates.json")) else {}
ETHQ = {Z: 1e-18, WETH: 1e-18, USDG: 1 / 2570 / 1e6}
if "SPCX_ETH" in rates: ETHQ[SPCX] = rates["SPCX_ETH"] / 1e18
QN = {Z: "ETH", WETH: "WETH", USDG: "USDG", SPCX: "SPCX"}
X = json.load(open(J("s01_launches.json"))); head = json.load(open(J("s03_head.json")))["head"]
R = {r["transactionHash"]: r for r in jl(C("s03_rcpt_cache.jsonl"))}
TX = {t["hash"]: t for t in jl(C("s03_tx_cache.jsonl"))}
ev = {}
for l in jl(C("s03_ev_cache.jsonl")) + jl(C("s03_ml_cache.jsonl")): ev[(l["transactionHash"], l["logIndex"])] = l
byp = collections.defaultdict(list)
for l in ev.values(): byp[l["topics"][1]].append(l)
P = []
for s, v in X.items():
    for x in v:
        rc = R[x["tx"]]
        minted = {l["address"].lower() for l in rc["logs"] if l["topics"] and l["topics"][0] == T_TRANSFER and len(l["topics"]) == 3 and int(l["topics"][1], 16) == 0}
        c0, c1 = x["c0"], x["c1"]
        if c1 in minted and c0 not in minted: coin, quote, qs = c1, c0, 0
        elif c0 in minted and c1 not in minted: coin, quote, qs = c0, c1, 1
        else: coin, quote, qs = (c1, c0, 0) if c0 in ETHQ else (c0, c1, 1)
        f = ETHQ.get(quote)
        p = {"shape": s, "pid": x["pid"], "lb": x["lb"], "li": x["li"], "tx": x["tx"], "launcher": x["from"], "target": x["to"], "n": x["n"], "value": x["value"],
             "fee": x["fee"], "ts": x["ts"], "hook": x["hook"], "sqrtP0": x["sqrtP"], "tick0": x["tick"], "coin": coin, "quote": quote, "qname": QN.get(quote, quote[:10]),
             "qs": qs, "sw": [], "ml": []}
        for l in sorted(byp[x["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
            bn = int(l["blockNumber"], 16); h = l["transactionHash"]; t = TX.get(h, {})
            base = {"off": bn - x["lb"], "bn": bn, "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16), "tx": h, "sender": "0x" + l["topics"][2][-40:],
                    "from": t.get("from"), "to": t.get("to"), "sel": t.get("sel"), "tn": t.get("n"), "tvalue": int(t["value"], 16) / 1e18 if t else None, "inlaunch": h == x["tx"]}
            if l["topics"][0] == T_SWAP:
                if bn > x["lb"] + WIN: continue
                a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1)); aq, ac = (a0, a1) if qs == 0 else (a1, a0)
                base.update({"buy": aq < 0, "q": abs(aq), "c": abs(ac), "eth": abs(aq) * f if f else None, "sqrtP": W(l["data"], 2), "liq": W(l["data"], 3),
                             "tick": sgn(W(l["data"], 4)), "swfee": W(l["data"], 5)})
                p["sw"].append(base)
            else:
                base.update({"lo": sgn(W(l["data"], 0)), "hi": sgn(W(l["data"], 1)), "dL": sgn(W(l["data"], 2))})
                p["ml"].append(base)
        pl = next((m for m in p["ml"] if m["dL"] < 0), None)
        p["pull"] = pl["off"] if pl else None
        p["pull_from"] = pl["from"] if pl else None
        p["age"] = head - x["lb"]
        P.append(p)
json.dump({"head": head, "pools": P}, open(J("s04_pools.json"), "w"))
for s in X:
    pp = [p for p in P if p["shape"] == s]
    print(f"===== {s}: {len(pp)} pools, launch wallets {len({p['launcher'] for p in pp})}, quotes {collections.Counter(p['qname'] for p in pp).most_common(5)}")
    print("  coin side: quote is currency%s" % dict(collections.Counter(p["qs"] for p in pp)))
    nsw = [sum(1 for w in p["sw"] if not w["inlaunch"]) for p in pp]
    print(f"  pools with a swap after the launch tx (to +{WIN}): {sum(1 for n in nsw if n)}; swaps {sum(nsw)}; launch-tx swaps {sum(1 for p in pp for w in p['sw'] if w['inlaunch'])}")
    lb_sw = [w for p in pp for w in p["sw"] if w["inlaunch"]]
    if lb_sw: print("  launch-tx swaps: buys", sum(w['buy'] for w in lb_sw), "ETH-eq p50", pct([w['eth'] or 0 for w in lb_sw], .5), "max", max(w['eth'] or 0 for w in lb_sw))
    pulled = [p for p in pp if p["pull"] is not None]
    print(f"  pulled: {len(pulled)} (within +{WIN}: {sum(1 for p in pulled if p['pull'] <= WIN)}); pull offsets {sorted(p['pull'] for p in pulled)[:30]}; puller==launcher {sum(1 for p in pulled if p['pull_from'] == p['launcher'])}")
    print(f"  ML events after the launch tx: {collections.Counter((m['dL'] > 0, m['to']) for p in pp for m in p['ml'] if not m['inlaunch']).most_common(6)}")
    buyers = collections.defaultdict(lambda: [0, 0.0, set(), []]); tos = collections.defaultdict(lambda: [0, 0.0, set()])
    for p in pp:
        for w in p["sw"]:
            if w["inlaunch"] or not w["buy"]: continue
            b = buyers[w["from"]]; b[0] += 1; b[1] += w["eth"] or 0; b[2].add(p["pid"]); b[3].append(w["off"])
            t = tos[(w["to"], w["sel"])]; t[0] += 1; t[1] += w["eth"] or 0; t[2].add(p["pid"])
    print(f"  buyers (after the launch tx): {len(buyers)} EOAs, {sum(b[0] for b in buyers.values())} buys, {sum(b[1] for b in buyers.values()):.4f} ETH-eq")
    for w, b in sorted(buyers.items(), key=lambda kv: -len(kv[1][2]))[:12]:
        print(f"    {w} pools {len(b[2]):3d} buys {b[0]:4d} ETH-eq {b[1]:.4f} offsets p10/50/90 {pct(b[3], .1)}/{pct(b[3], .5)}/{pct(b[3], .9)} launcher? {w in {p['launcher'] for p in pp}}")
    print("  buy targets (to, selector): ")
    for k, t in sorted(tos.items(), key=lambda kv: -len(kv[1][2]))[:8]: print(f"    {k} pools {len(t[2])} buys {t[0]} ETH-eq {t[1]:.4f}")
