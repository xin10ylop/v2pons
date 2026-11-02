#!/usr/bin/env python3
"""structlab.py CHAIN OUT.json DAY...: every launch shape on a chain tested for a scripted buyer, whoever runs it and whether or not anyone
trades it yet (the census days given: out/CHAIN_DAY_00.json).

Why: the earlier sweeps found lines through their outcomes. front.py tested the front seat on pulled pools launched with 0.5+ native only
(C-1 launches token-only and was missed); allfront.py read every pool but found lines through the round trips other traders made, so a
scripted buyer nobody fronts yet leaves no trace there. This reads every pool the census saw created, groups the pools by their launch
(the venue, the launch transaction's target, selector, calldata length and value to 3 significant figures; v4: fee, tick spacing and
whether a hook is set), and asks of each group the 2.433 questions:

  big       the first buy of BIG native or more after the launch block (the scripted buyer's, if there is one): how often it comes within
            WIN blocks, at what offset, what size, through which contract (one target in most pools = one bot), by how many senders
  front     paper, 2.433-style: buy STAKE native at the head of launch + 2 (the engine's landing), sell in the block after the big buy, on the
            recorded reserves with our buy kept in the pool; no big buy by WIN: sold at WIN; a pull at or before the sell: -100%
  behind    paper, C-1-style: buy at the head of the big buy's block + 2, sell 20 / 100 blocks later (a pull first: -100%)
  reaction  pools where an outsider (not the launch wallet, not the big buy's contract) bought 0.001+ native after the launch block and
            before the big buy: does the big buy still come (and no pull before it)? Against the pools nobody bought ahead of. The
            2.433 line answered yes until it closed; a closed line answers no
  hook      v4 groups: pools whose hook may rewrite a swap's amounts (beforeSwap/afterSwap return-delta flags): never traded (sells may fail)

Prints the groups with MIN_POOLS (10) pools or more, ranked by the front seat's paper ETH a day at STAKE, then by the behind ride's.
Read-only, public RPCs. Env: WIN (blocks, default 600 Robinhood / 30 Base), BIG (0.02), STAKE (0.005), MIN_POOLS (10)."""
import os, sys, json, collections, statistics as st
import hlib as H
from tape import fetch, events

CH = sys.argv[1]; OUT = sys.argv[2]; DAYS = sys.argv[3:]
WIN = int(os.environ.get("WIN", "600" if CH == "rh" else "30")); BIG = float(os.environ.get("BIG", "0.02"))
STAKE = float(os.environ.get("STAKE", "0.005")); MIN_POOLS = int(os.environ.get("MIN_POOLS", "10")); GAS = 0.000006
WN = {"rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "base": "0x4200000000000000000000000000000000000006"}[CH]
T_INIT4 = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"   # v4 PoolManager Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)
HERE = os.path.dirname(os.path.abspath(__file__))
url = H.CH[CH]["rpc"]


def sig3(v):
    return 0 if v <= 0 else float(f"{v:.3g}")


def load_cache(name):
    try:
        return json.load(open(os.path.join(HERE, "out", name)))
    except (OSError, ValueError):
        return {}


def txs_of(hashes, cache):
    need = sorted({h for h in hashes if h not in cache})
    got = H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=10) if need else []
    for h, x in zip(need, got):
        if x:
            cache[h] = [x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], (len(x["input"]) - 2) // 2, int(x["value"], 16) / 1e18]
    return cache


def main():
    P = {}; bt = None
    for d in DAYS:
        r = json.load(open(os.path.join(HERE, f"out/{CH}_{d}_00.json")))["chains"][CH]; bt = r["bt"]
        rug = {p["id"]: p for p in r["rugs"]}
        for k, tok, bn, tx, nin in r["created"]:
            venue = k.split(":")[0]
            P[k] = {"id": k, "venue": venue, "tok": tok.lower(), "bn": bn, "tx": tx, "nin": nin or 0, "day": d,
                    "nat": 0 if venue == "v4" or WN < tok.lower() else 1, "rem_bn": bn + WIN + 2, "pull": rug[k]["rem_bn"] if k in rug else None}
    print(f"{CH} {DAYS[0]}..{DAYS[-1]}: {len(P)} pools created", flush=True)
    lc = load_cache(f"struct_launch_{CH}.json"); txs_of([p["tx"] for p in P.values()], lc)
    json.dump(lc, open(os.path.join(HERE, "out", f"struct_launch_{CH}.json"), "w"))
    print(f"  launch transactions read: {sum(1 for p in P.values() if p['tx'] in lc)}", flush=True)
    v4 = sorted((p for p in P.values() if p["venue"] == "v4"), key=lambda p: p["bn"])
    if v4:                                                                         # each v4 pool's fee, tick spacing and hook (its Initialize)
        il = H.logs(CH, v4[0]["bn"], v4[-1]["bn"], [T_INIT4], H.CH[CH]["pm"])
        ini = {x["topics"][1]: x["data"][2:] for x in il}
        for p in v4:
            d = ini.get(p["id"][3:])
            if d:
                p["fee"], p["ts"] = int(d[0:64], 16), H.i256(d[64:128]); p["hooks"] = int(d[128:192], 16)
    L = fetch(CH, list(P.values()))
    per = collections.defaultdict(list)
    for x in L:
        per[("v4:" + x["topics"][1]) if x["topics"][0] == H.T_SWAP4 else (("v2:" if x["topics"][0] != H.T_SWAP3 else "v3:") + x["address"].lower())].append(x)
    for p in P.values():
        p["ev"] = [e for e in events(p, per.get(p["id"], [])) if e[0] <= p["bn"] + WIN]
        fs = [int(x["data"][2:][320:384], 16) for x in per.get(p["id"], []) if p["venue"] == "v4" and len(x["data"]) >= 2 + 384]
        p["f"] = (st.median(fs) / 1e6 if fs else (p.get("fee", 3000) / 1e6)) if p["venue"] == "v4" else (0.003 if p["venue"] == "v2" else None)
    if any(p["venue"] == "v3" for p in P.values()):                              # a V3 pool's fee from the pool itself
        v3 = sorted(k for k, p in P.items() if p["venue"] == "v3")
        fz = H.batch(url, [("eth_call", [{"to": k[3:], "data": "0xddca3f43"}, "latest"]) for k in v3], size=50, workers=2, tries=6)
        for k, f in zip(v3, fz):
            P[k]["f"] = int(f, 16) / 1e6 if f and f != "0x" else 0.003
    print(f"  swaps read: {sum(len(p['ev']) for p in P.values())}", flush=True)
    for p in P.values():                                                           # the big buy and the buys ahead of it
        p["big"] = next((e for e in p["ev"] if e[0] > p["bn"] and e[2] >= BIG), None)
        p["pre"] = [e for e in p["ev"] if p["bn"] < e[0] < (p["big"][0] if p["big"] else p["bn"] + WIN + 1) and e[2] >= 0.001]
    tc = load_cache(f"struct_tx_{CH}.json")
    txs_of([p["big"][6] for p in P.values() if p["big"]] + [e[6] for p in P.values() for e in p["pre"]], tc)
    json.dump(tc, open(os.path.join(HERE, "out", f"struct_tx_{CH}.json"), "w"))

    def state_before(p, b):
        """the pool's native and token reserves at the head of block b: after the last swap before b, else before the first swap"""
        prior = [e for e in p["ev"] if e[0] < b and e[4]]
        if prior:
            return prior[-1][4], prior[-1][5]
        first = next((e for e in p["ev"] if e[4]), None)
        return (first[4] - first[2] * (1 - p["f"]), first[5] + first[3]) if first else (None, None)

    def ride(p, entry, exit_b):
        """our STAKE in at the head of `entry`, out at the end of `exit_b` (after its swaps), our buy kept in the pool"""
        if p["pull"] is not None and p["pull"] <= exit_b:
            return -1.0
        x, y = state_before(p, entry)
        if not x or not y or x <= 0 or y <= 0:
            return None
        s = STAKE * (1 - p["f"]); q = y - x * y / (x + s)
        x2, y2 = state_before(p, exit_b + 1)
        x2 += s; y2 -= q
        if y2 <= 0:
            return None
        back = x2 - x2 * y2 / (y2 + q * (1 - p["f"]))
        return (back - STAKE - GAS) / STAKE

    G = collections.defaultdict(list)
    for p in P.values():
        t = lc.get(p["tx"])
        if not t:
            continue
        key = (p["venue"], t[1][:10], t[2], t[3], sig3(t[4])) + ((p.get("fee"), p.get("ts"), "hook" if p.get("hooks") else "") if p["venue"] == "v4" else (round(p["f"] * 1e6),))
        p["launcher"] = t[0]; G[key].append(p)
    days = len(DAYS); rows = []
    for key, ps in G.items():
        if len(ps) < MIN_POOLS:
            continue
        bigs = [p for p in ps if p["big"]]
        offs = sorted(p["big"][0] - p["bn"] for p in bigs); sizes = [p["big"][2] for p in bigs]
        tos = collections.Counter(tc.get(p["big"][6], [None, None])[1] for p in bigs); senders = {tc.get(p["big"][6], [None])[0] for p in bigs}
        self_buy = sum(1 for p in bigs if tc.get(p["big"][6], [None])[0] == p["launcher"])
        top_to, top_n = tos.most_common(1)[0] if tos else (None, 0)
        fr = [r for r in (ride(p, p["bn"] + 2, (p["big"][0] + 1) if p["big"] and p["big"][0] - p["bn"] >= 3 else p["bn"] + WIN) for p in ps
                          if not p["big"] or p["big"][0] - p["bn"] >= 3) if r is not None]
        b20 = [r for r in (ride(p, p["big"][0] + 2, p["big"][0] + 22) for p in bigs if p["big"][0] + 22 <= p["bn"] + WIN) if r is not None]
        b100 = [r for r in (ride(p, p["big"][0] + 2, p["big"][0] + 102) for p in bigs if p["big"][0] + 102 <= p["bn"] + WIN) if r is not None]
        def outsider(p):
            bt_ = tc.get(p["big"][6], [None, None])[1] if p["big"] else None
            return [e for e in p["pre"] if tc.get(e[6], [None, None])[0] not in (p["launcher"], None) and tc.get(e[6], [None, None])[1] != bt_]
        fronted = [p for p in ps if outsider(p)]; clean = [p for p in ps if not outsider(p)]
        came = lambda qs: sum(1 for p in qs if p["big"] and (p["pull"] is None or p["pull"] > p["big"][0] + 1)) / len(qs) if qs else None
        hooked = sum(1 for p in ps if p.get("hooks") and (p["hooks"] & 0b1100))
        rows.append({"key": key, "pools": len(ps), "per_day": len(ps) / days, "pulled_2h": sum(1 for p in ps if p["pull"] is not None) / len(ps),
                     "launch_native_median": st.median(p["nin"] for p in ps), "big_share": len(bigs) / len(ps),
                     "big_off": (offs[len(offs) // 4], st.median(offs), offs[3 * len(offs) // 4]) if offs else None, "big_size_median": st.median(sizes) if sizes else None,
                     "big_top_to": top_to, "big_top_share": top_n / len(bigs) if bigs else None, "big_senders": len(senders), "big_by_launcher": self_buy / len(bigs) if bigs else None,
                     "front_n": len(fr), "front_mean": st.mean(fr) if fr else None, "front_won": sum(r > 0 for r in fr) / len(fr) if fr else None, "front_pulled": sum(r <= -1 for r in fr),
                     "behind20": st.mean(b20) if b20 else None, "behind100": st.mean(b100) if b100 else None, "behind100_n": len(b100), "behind100_pulled": sum(r <= -1 for r in b100),
                     "fronted_n": len(fronted), "fronted_came": came(fronted), "clean_came": came(clean), "hook_delta": hooked,
                     "front_eth_day": (st.mean(fr) * STAKE * len(fr) / days) if fr else 0.0, "behind_eth_day": (st.mean(b100) * STAKE * len(b100) / days) if b100 else 0.0})
    rows.sort(key=lambda r: -max(r["front_eth_day"], r["behind_eth_day"]))
    json.dump({"chain": CH, "days": DAYS, "win": WIN, "big": BIG, "stake": STAKE, "rows": rows}, open(OUT, "w"), default=str)
    f = lambda v, fmt: "-" if v is None else format(v, fmt)
    print(f"\n{len(rows)} launch groups with {MIN_POOLS}+ pools; paper at {STAKE:g} native a trade; big buy = first buy of {BIG:g}+ within {WIN} blocks")
    for r in rows[:40]:
        k = r["key"]
        print(f"{'/'.join(str(x) for x in k)}\n    pools {r['pools']} ({r['per_day']:.0f}/day), pulled 2h {r['pulled_2h']:.0%}, launch native {r['launch_native_median']:.3g}{', HOOK-DELTA ' + str(r['hook_delta']) if r['hook_delta'] else ''}"
              f" | big buy in {r['big_share']:.0%} at +{r['big_off'][1] if r['big_off'] else '-'} (p25 {r['big_off'][0] if r['big_off'] else '-'}, p75 {r['big_off'][2] if r['big_off'] else '-'}),"
              f" size {f(r['big_size_median'], '.3g')}, top target {str(r['big_top_to'])[:10]} {f(r['big_top_share'], '.0%')}, senders {r['big_senders']}, by launcher {f(r['big_by_launcher'], '.0%')}\n"
              f"    FRONT n {r['front_n']} mean {f(r['front_mean'], '+.1%')} won {f(r['front_won'], '.0%')} pulled {r['front_pulled']} -> {r['front_eth_day']:+.4f}/day"
              f" | BEHIND h20 {f(r['behind20'], '+.1%')} h100 {f(r['behind100'], '+.1%')} (n {r['behind100_n']}, pulled {r['behind100_pulled']}) -> {r['behind_eth_day']:+.4f}/day"
              f" | fronted {r['fronted_n']}: big came {f(r['fronted_came'], '.0%')} (clean {f(r['clean_came'], '.0%')})")


if __name__ == "__main__":
    main()
