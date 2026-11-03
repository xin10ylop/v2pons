#!/usr/bin/env python3
"""buyerlab.py CHAIN OUT.json DAY...: blind scheduled buyers, searched by the buyer instead of the launch.

The 2.433 seat was a bot that bought every launch of its line at a fixed delay with a fixed size, whoever had bought before it: buy
ahead of it, sell into its buy. structlab.py looked for that per launch template and only at the first big buy. This groups every buy in
the first WIN blocks of every pool the census saw created (out/CHAIN_DAY_00.json) by the buyer, whatever pool or launcher:
  buyer     the contract that called the pool (v4: the Swap's sender; V3/V2: its sender), or, when that is a public router, the
            transaction's sender (read for buys of MIN_ETH and up)
  scheduled for each buyer in MIN_POOLS+ pools: its first buy's offset from the launch (median, IQR, the share within +-3 blocks of
            the median) and size (median, spread): a tight offset and size is a scheduled bot
  blind     among the launch groups (structlab's key) it buys in: P(it buys | an outsider, not the line's crew (buyers in 10%+ of its
            pools), bought before its usual offset) against
            P(it buys | nobody did); a blind bot buys either way
  front     paper: STAKE in at the head of max(launch + 2, its buy - LEAD), out at the end of its buy's block + 1, on the recorded
            reserves with our buy kept in the pool (a pull first: -100%); per buyer: mean, won, pulled, pools a day, ETH a day
Prints the buyers ranked by the front's paper ETH a day. Read-only, public RPCs. Env: WIN (600 RH / 300 Base blocks), MIN_POOLS (15),
MIN_ETH (0.002), STAKE (0.005), LEAD (5)."""
import os, sys, json, collections, statistics as st
import hlib as H
from eth_utils import keccak
from tape import fetch, events

CH = sys.argv[1]; OUT = sys.argv[2]; DAYS = sys.argv[3:]
WIN = int(os.environ.get("WIN", {"rh": "6000", "base": "300", "bnb": "1300", "eth": "50"}[CH])); MIN_POOLS = int(os.environ.get("MIN_POOLS", "15"))
MIN_ETH = float(os.environ.get("MIN_ETH", "0.002")); STAKE = float(os.environ.get("STAKE", "0.005")); LEAD = int(os.environ.get("LEAD", "5")); GAS = 0.000006
WN = {"rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "base": "0x4200000000000000000000000000000000000006", "bnb": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c", "eth": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"}[CH]
PUBLIC = {"rh": {"0x8876789976decbfcbbbe364623c63652db8c0904", "0xcaf681a66d020601342297493863e78c959e5cb2", "0x89e5db8b5aa49aa85ac63f691524311aeb64ed43"},
          "base": {"0x6ff5693b99212da76ad316178a184ab56d299b43", "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x2626664c2603336e57b271c5c0b26f421741e481",
                   "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x8cfe327cec66d1c090dd72bd0ff11d690c33a2eb"},
          "bnb": {"0x10ed43c718714eb63d5aa57b78b54704e256024e", "0x13f4ea83d0bd40e75c8222255bc855a974568dd4", "0x1906c1d672b88cd1b9ac7593301ca990f94eae07",
                  "0xd9c500dff816a1da21a48a732d3498bf09dc9aeb", "0x111111125421ca6dc452d289314280a0f8842a65", "0x1b81d678ffb9c0263b24a97847620c99d213eb14"},
          "eth": {"0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x66a9893cc07d91d95644aedd05d03f95e1dba8af", "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
                  "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", "0x111111125421ca6dc452d289314280a0f8842a65", "0x3328f7f4a1d1c57c35df56bbf0c9dcafca309c49",
                  "0x80a64c6d7f12c47b7c66c5b4e20e72bc1fcd5d9e", "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f"}}[CH]   # UR, UR (v4), V2 router, SwapRouter02, 1inch, Banana Gun, Maestro, Sushi   # Pancake V2 / smart / universal, Uniswap UR, 1inch, Pancake V3 router
HERE = os.path.dirname(os.path.abspath(__file__)); url = H.CH[CH]["rpc"]


def main():
    P = {}
    for d in DAYS:
        r = json.load(open(os.path.join(HERE, f"out/{CH}_{d}_00.json")))["chains"][CH]
        rug = {p["id"]: p for p in r["rugs"]}
        for k, tok, bn, tx, nin in r["created"]:
            venue = k.split(":")[0]
            P[k] = {"id": k, "venue": venue, "tok": tok.lower(), "bn": bn, "tx": tx, "nin": nin or 0, "day": d, "nat": 0 if venue == "v4" or WN < tok.lower() else 1,
                    "rem_bn": bn + WIN + 2, "pull": rug[k]["rem_bn"] if k in rug else None}
    print(f"{CH} {DAYS[0]}..{DAYS[-1]}: {len(P)} pools", flush=True)
    try:
        lc = json.load(open(os.path.join(HERE, "out", f"struct_launch_{CH}.json")))
    except (OSError, ValueError):
        lc = {}
    miss = sorted({p["tx"] for p in P.values() if p["tx"] not in lc})                 # the launch transactions (the launcher, the group): read once, cached with structlab's
    for i in range(0, len(miss), 2000):
        g = miss[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
            if x:
                lc[h] = [x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], (len(x["input"]) - 2) // 2, int(x["value"], 16) / 1e18]
        json.dump(lc, open(os.path.join(HERE, "out", f"struct_launch_{CH}.json"), "w"))
    print(f"  launch transactions: {sum(1 for p in P.values() if p['tx'] in lc)} of {len(P)}", flush=True)
    L = fetch(CH, list(P.values()))
    per = collections.defaultdict(list)
    for x in L:
        per[("v4:" + x["topics"][1]) if x["topics"][0] == H.T_SWAP4 else (("v3:" if x["topics"][0] in (H.T_SWAP3, H.T_SWAP3_PCS) else "v2:") + x["address"].lower())].append(x)
    print(f"  logs: {len(L)}", flush=True)
    need = []
    for p in P.values():
        logs = sorted(per.get(p["id"], []), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
        p["ev"] = [e for e in events(p, logs) if e[0] <= p["bn"] + WIN]
        who = {}
        for x in logs:
            if x["topics"][0] not in (H.T_SWAP4, H.T_SWAP3, H.T_SWAP3_PCS, H.T_SWAP2):
                continue
            snd = "0x" + x["topics"][2][26:] if x["topics"][0] == H.T_SWAP4 else "0x" + x["topics"][1][26:]
            rcp = None if x["topics"][0] == H.T_SWAP4 else "0x" + x["topics"][2][26:]
            who[(int(x["blockNumber"], 16), int(x["logIndex"], 16))] = (snd, rcp, x["transactionHash"])
        p["who"] = who
        for e in p["ev"]:
            w = who.get((e[0], e[1]))
            if w and w[0] in PUBLIC and e[2] >= MIN_ETH:
                need.append(w[2])
    cache_p = os.path.join(HERE, "out", f"buyer_tx_{CH}.json")
    try:
        tc = json.load(open(cache_p))
    except (OSError, ValueError):
        tc = {}
    todo = sorted(set(h for h in need if h not in tc))
    print(f"  public-router buys to resolve: {len(todo)}", flush=True)
    for i in range(0, len(todo), 2000):
        g = todo[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
            tc[h] = x["from"].lower() if x else None
        json.dump(tc, open(cache_p, "w"))
    v3 = sorted(k for k, p in P.items() if p["venue"] == "v3")                       # a V3 pool's fee from the pool itself
    fz = H.batch(url, [("eth_call", [{"to": k[3:], "data": "0xddca3f43"}, "latest"]) for k in v3], size=50, workers=2, tries=6) if v3 else []
    v3fee = {k: (int(f, 16) / 1e6 if f and f != "0x" else 0.003) for k, f in zip(v3, fz)}
    code_p = os.path.join(HERE, "out", f"token_code_{CH}.json")                       # each token's code: keccak (12 hex) and length
    try:
        cc = json.load(open(code_p))
    except (OSError, ValueError):
        cc = {}
    tk = sorted({p["tok"] for p in P.values() if p["tok"] not in cc})
    for i in range(0, len(tk), 2000):
        g = tk[i:i + 2000]
        for t, c in zip(g, H.batch(url, [("eth_getCode", [t, "latest"]) for t in g], size=50, workers=4, tries=10)):
            cc[t] = [keccak(bytes.fromhex(c[2:])).hex()[:12], (len(c) - 2) // 2] if c and len(c) > 2 else ["nocode", 0]
        json.dump(cc, open(code_p, "w"))
    hc = collections.Counter(cc.get(p["tok"], ["?", 0])[0] for p in P.values())
    for p in P.values():
        fs = [x for x in per.get(p["id"], []) if p["venue"] == "v4" and x["topics"][0] == H.T_SWAP4 and len(x["data"]) >= 2 + 384]
        p["f"] = (st.median(int(x["data"][2:][320:384], 16) for x in fs) / 1e6 if fs else 0.003) if p["venue"] == "v4" else 0.003 if p["venue"] == "v2" else v3fee.get(p["id"], 0.003)
        t = lc.get(p["tx"]); p["launcher"] = t[0] if t else None
        p["tmpl"] = (p["venue"], t[1][:10], t[2], t[3]) if t else (p["venue"], "?")                 # the launch call (shown)
        h, ln = cc.get(p["tok"], ["?", 0])
        p["grp"] = (p["venue"], "code " + h) if hc[h] >= 3 else (p["venue"], f"{ln} B")             # the line: the token's template (its code, or its length when every copy differs)
    # every buy of MIN_ETH+ in the window, by its buyer
    buys = collections.defaultdict(dict)                       # buyer -> pool id -> (offset, eth, block)
    for p in P.values():
        for e in p["ev"]:
            if e[2] < MIN_ETH or e[0] <= p["bn"]:
                continue
            w = p["who"].get((e[0], e[1]))
            if not w:
                continue
            key = (tc.get(w[2]) or "?") if w[0] in PUBLIC else w[0]
            if key in ("?", None) or key == p["launcher"]:
                continue
            buys[key].setdefault(p["id"], (e[0] - p["bn"], e[2], e[0], w[2]))
    # a contract called by many wallets is a router (an aggregator, a Telegram bot's contract, an operator's crowd router): kept as a buyer,
    # and its callers become buyers of their own (each its first buy through it in a pool)
    multi = {}
    for key, bp in list(buys.items()):
        if len(bp) < MIN_POOLS or key in PUBLIC:
            continue
        hs = [v[3] for v in list(bp.values())[:30]]; miss = [h for h in hs if h not in tc]
        for h, x in zip(miss, H.batch(url, [("eth_getTransactionByHash", [h]) for h in miss], size=50, workers=4, tries=10) if miss else []):
            tc[h] = x["from"].lower() if x else None
        frm = {tc.get(h) for h in hs} - {None}
        if len(frm) >= 6:
            multi[key] = len(frm)
    if multi:
        need = [w[2] for p in P.values() for e in p["ev"] for w in [p["who"].get((e[0], e[1]))] if w and w[0] in multi and e[2] >= MIN_ETH and w[2] not in tc]
        need = sorted(set(need))
        print(f"  contracts called by many wallets: {len(multi)}; their buys to resolve: {len(need)}", flush=True)
        for i in range(0, len(need), 2000):
            g = need[i:i + 2000]
            for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
                tc[h] = x["from"].lower() if x else None
            json.dump(tc, open(cache_p, "w"))
        for p in P.values():
            for e in p["ev"]:
                w = p["who"].get((e[0], e[1]))
                if w and w[0] in multi and e[2] >= MIN_ETH and e[0] > p["bn"]:
                    k2 = tc.get(w[2])
                    if k2 and k2 != p["launcher"]:
                        buys[k2].setdefault(p["id"], (e[0] - p["bn"], e[2], e[0], w[2]))
    print(f"  buyers with {MIN_POOLS}+ pools: {sum(1 for b in buys.values() if len(b) >= MIN_POOLS)}", flush=True)

    def state_before(p, b):
        prior = [e for e in p["ev"] if e[0] < b and e[4]]
        if prior:
            return prior[-1][4], prior[-1][5]
        first = next((e for e in p["ev"] if e[4]), None)
        return (first[4] - first[2] * (1 - p["f"]), first[5] + first[3]) if first else (None, None)

    def ride(p, entry, exit_b):
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
        return (x2 - x2 * y2 / (y2 + q * (1 - p["f"])) - STAKE - GAS) / STAKE

    days = len(DAYS); rows = []
    gsize = collections.Counter(p["grp"] for p in P.values())                     # a line's crew: every buyer in 10%+ of its pools (3 at least): never an outsider
    in_grp = collections.defaultdict(collections.Counter)
    for key, bp in buys.items():
        for pid in bp:
            in_grp[P[pid]["grp"]][key] += 1
    crew = {g: {k for k, n in c.items() if n >= max(3, 0.1 * gsize[g])} for g, c in in_grp.items()}
    early = {}                                                                     # every pool's buys of 0.001+ after the launch block: (offset, buyer), resolved once
    for p in P.values():
        lst = []
        for e in p["ev"]:
            if e[0] > p["bn"] and e[2] >= 0.001:
                w = p["who"].get((e[0], e[1]))
                if w:
                    lst.append((e[0] - p["bn"], (tc.get(w[2]) if (w[0] in PUBLIC or w[0] in multi) else w[0])))
        early[p["id"]] = lst
    for key, bp in buys.items():
        if len(bp) < MIN_POOLS:
            continue
        offs = sorted(v[0] for v in bp.values()); sizes = [v[1] for v in bp.values()]; med = st.median(offs)
        tight = sum(1 for o in offs if abs(o - med) <= 3) / len(offs)
        grps = collections.Counter(P[pid]["grp"] for pid in bp)
        fr = []
        for pid, (o, eth, b, _h) in bp.items():
            if o < 4:
                continue
            r = ride(P[pid], max(P[pid]["bn"] + 2, b - LEAD), b + 1)
            if r is not None:
                fr.append(r)
        # blindness: in its main launch groups, pools where an outsider (not it, not the launcher) bought 0.001+ before its usual offset
        main = [g for g, n in grps.items() if n >= 5]
        seen = [p for p in P.values() if p["grp"] in main]
        lim = max(4, med); cr = crew
        def early_outsider(p):
            return any(o < lim and k2 not in (key, p["launcher"], None) and k2 not in cr.get(p["grp"], ()) for o, k2 in early[p["id"]])
        a = [p for p in seen if early_outsider(p)]; c = [p for p in seen if not early_outsider(p)]
        rows.append({"buyer": key, "pools": len(bp), "per_day": len(bp) / days, "off_med": med, "off_iqr": (offs[len(offs) // 4], offs[3 * len(offs) // 4]), "tight": tight,
                     "size_med": st.median(sizes), "size_spread": (min(sizes), max(sizes)), "groups": grps.most_common(3),
                     "bought_if_fronted": (sum(1 for p in a if p["id"] in bp) / len(a)) if a else None, "fronted_n": len(a),
                     "bought_if_clean": (sum(1 for p in c if p["id"] in bp) / len(c)) if c else None, "clean_n": len(c),
                     "front_n": len(fr), "front_mean": st.mean(fr) if fr else None, "front_won": sum(r > 0 for r in fr), "front_pulled": sum(r <= -1 for r in fr),
                     "front_eth_day": st.mean(fr) * STAKE * len(fr) / days if fr else 0.0, "multi_sender": multi.get(key),
                     "templates": collections.Counter(P[pid]["tmpl"] for pid in bp).most_common(2)})
    rows.sort(key=lambda r: -r["front_eth_day"])
    if os.environ.get("DUMP"):                                                      # per-pool detail for a line analysis (fleetlab.py)
        dump = {"pools": {k: {"bn": p["bn"], "tok": p["tok"], "launcher": p["launcher"], "grp": list(p["grp"]), "pull": p["pull"], "venue": p["venue"], "f": p["f"],
                              "ev": [e[:6] for e in p["ev"]],
                              "buyers": [[e[0], e[1], e[2], ((tc.get(w[2]) or "?") if w[0] in PUBLIC else w[0])] for e in p["ev"] for w in [p["who"].get((e[0], e[1]))] if w and e[2] > 0]}
                          for k, p in P.items()},
                "buys": {k: v for k, v in buys.items() if len(v) >= MIN_POOLS}}
        json.dump(dump, open(os.environ["DUMP"], "w"))
    json.dump({"chain": CH, "days": DAYS, "rows": rows}, open(OUT, "w"), default=str)
    f = lambda v, fmt: "-" if v is None else format(v, fmt)
    def show(r):
        print(f"{r['buyer']}{' [called by ' + str(r['multi_sender']) + '+ wallets]' if r['multi_sender'] else ''}  pools {r['pools']} ({r['per_day']:.0f}/day)  first buy at +{r['off_med']:g}"
              f" (IQR {r['off_iqr'][0]}..{r['off_iqr'][1]}, {r['tight']:.0%} within 3)  size {r['size_med']:.4g} ({r['size_spread'][0]:.3g}..{r['size_spread'][1]:.3g})\n"
              f"    FRONT n {r['front_n']} mean {f(r['front_mean'], '+.1%')} won {r['front_won']} pulled {r['front_pulled']} -> {r['front_eth_day']:+.4f}/day"
              f" | buys when a real outsider was first {f(r['bought_if_fronted'], '.0%')} (n {r['fronted_n']}) vs clean {f(r['bought_if_clean'], '.0%')} (n {r['clean_n']})"
              f" | lines {[(tuple(g)[1:], n) for g, n in r['groups']]} | launch calls {[(tuple(g)[1:], n) for g, n in r['templates']]}")
    print(f"\n{len(rows)} buyers in {MIN_POOLS}+ pools; window {WIN} blocks; front at {STAKE:g} native: in at max(launch + 2, its buy - {LEAD}), out after its buy")
    print("\n== BLIND: buys in half or more of its line's pools where a real outsider bought first (3+ such pools) ==")
    for r in [r for r in rows if r["bought_if_fronted"] is not None and r["fronted_n"] >= 3 and r["bought_if_fronted"] >= 0.5][:25]:
        show(r)
    print("\n== UNTESTED: no real outsider bought ahead of it in 3+ pools of its line; front +3% or better, 5+ pools a day ==")
    for r in [r for r in rows if r["fronted_n"] < 3 and (r["front_mean"] or 0) >= 0.03 and r["per_day"] >= 5][:25]:
        show(r)
    print("\n== TOP BY THE FRONT'S PAPER ==")
    for r in rows[:25]:
        show(r)


if __name__ == "__main__":
    main()
