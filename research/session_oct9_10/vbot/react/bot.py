#!/usr/bin/env python3
"""The volume bot's own schedule in the census pools (txs complete to min(pull, +300)): its 1st/2nd buys (block, size), whether the 2nd
comes by +40, its sells (who, when, what fraction of that wallet's tokens), wallet reuse, and the inter-trade gaps."""
import sys, os, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX)
def q(xs, qs=(0, .05, .25, .5, .75, .95, 1)):
    xs = sorted(xs); return [round(xs[int(a * (len(xs) - 1))], 4) for a in qs] if xs else None
OUT = {}
for fam in ("v3.0", "v5.0", "v2.433"):
    b1, b2, s1, gaps, by40, n40, sellfrac, sell_after_next, wal_pools, buys_per_w, b1eth, b2eth, allbuy = [], [], [], [], 0, 0, [], [], collections.Counter(), [], [], [], []
    no2 = collections.Counter(); n_pool = 0
    for v in P.values():
        if v["fam"] != fam or v["src"] != "census": continue
        n_pool += 1
        lim = min(300, v["pull"] if v["pull"] is not None else 10**9)
        seq = []
        for s in v["sw"]:
            if s["rel"] > lim: break
            k, t = cls(v, s)
            if k == "bot": seq.append((s, t))
        bb = [(s, t) for s, t in seq if s["eth"] > 0]; bs = [(s, t) for s, t in seq if s["eth"] < 0]
        if bb: b1.append(bb[0][0]["rel"]); b1eth.append(bb[0][0]["eth"])
        if len(bb) > 1: b2.append(bb[1][0]["rel"]); b2eth.append(bb[1][0]["eth"])
        allbuy += [s["eth"] for s, t in bb]
        if bs: s1.append(bs[0][0]["rel"])
        alive40 = v["pull"] is None or v["pull"] > 40
        if alive40 and bb:
            n40 += 1
            if len(bb) > 1 and bb[1][0]["rel"] <= 40: by40 += 1
            else: no2[(bb[1][0]["rel"] if len(bb) > 1 else None)] += 1
        ev = [s["rel"] for s, t in seq]; gaps += [b - a for a, b in zip(ev, ev[1:])]
        hold = collections.defaultdict(int); wb = collections.Counter()
        for i, (s, t) in enumerate(seq):
            w = t["from"]
            if s["eth"] > 0: hold[w] += s["tok"]; wb[w] += 1
            else:
                if hold[w] > 0: sellfrac.append(-s["tok"] / hold[w]); hold[w] += s["tok"]
                nb = [x for x in bb if x[0]["rel"] <= s["rel"] and x[1]["from"] != w]
                mine = [x for x in bb if x[1]["from"] == w and x[0]["rel"] <= s["rel"]]
                if mine:
                    after = [x for x in nb if x[0]["rel"] >= mine[-1][0]["rel"]]
                    sell_after_next.append(len(after))
        for w in wb: wal_pools[w] += 1
        buys_per_w += list(wb.values())
    OUT[fam] = {"pools": n_pool, "b1_rel": q(b1), "b1_eth": q(b1eth), "b2_rel": q(b2), "b2_eth": q(b2eth), "all_buy_eth": q(allbuy), "first_sell_rel": q(s1),
                "b2_by_40_of_alive_at_40": [by40, n40], "no_b2_by_40_rel_of_b2": dict(no2.most_common(8)), "gap": q(gaps), "sell_fraction_of_holding": q(sellfrac),
                "other_bot_buys_between_own_buy_and_sell": dict(collections.Counter(sell_after_next).most_common(6)),
                "wallets": len(wal_pools), "pools_per_wallet": q(list(wal_pools.values())), "buys_per_wallet_per_pool": dict(collections.Counter(buys_per_w).most_common(4))}
    print(fam, json.dumps(OUT[fam], indent=None))
json.dump(OUT, open(os.path.join(HERE, "bot.json"), "w"), indent=1)
