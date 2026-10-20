#!/usr/bin/env python3
"""line_adapt: every bot buy (router c1120e3d) in the first 1,200 blocks: its rank in the pool, offset, gap to the previous one, size, its minOut
(word 4) vs the launch-state quote and vs the quote at the state just before it; the bot wallet's sell (UR) after its buy: when and how much.
-> botbuys.json and a printed summary per family and regime"""
import sys, os, json, time, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
NEW_FROM = int(time.mktime(time.strptime("2026-10-11 04:22:19", "%Y-%m-%d %H:%M:%S"))) - time.timezone
R = json.load(open(os.path.join(D, "rec.json")))
rows = []
for r in R:
    if not r["complete"]: continue
    sw = sorted(r["swaps"], key=lambda s: (s["off"], s["li"])); prev_sp = r["sp0"]; k = 0; last = None
    for i, s in enumerate(sw):
        if s["bot"] and s["side"] == "B":
            X2 = -s["a0"]
            q0 = v4math.buy_out_int(r["sp0"], r["L0"], X2, r["fee"]); qn = v4math.buy_out_int(prev_sp, s["L"], X2, r["fee"])
            sell = next((t for t in sw[i + 1:] if t["side"] == "S" and t["from"] == s["from"]), None)
            rows.append({"fam": r["fam"], "new": r["ts0"] >= NEW_FROM, "rank": k, "off": s["off"], "gap": s["off"] - last if last is not None else None, "eth": X2 / 1e18,
                         "mo_launch": s["minout"] / q0, "mo_now": s["minout"] / qn, "w2_is_token": s["w2"] == r["token"], "sell_after": (sell["off"] - s["off"]) if sell else None,
                         "sell_eth": sell["a0"] / 1e18 if sell else None, "from": s["from"]})
            k += 1; last = s["off"]
        prev_sp = s["sp"]
json.dump(rows, open(os.path.join(HERE, "botbuys.json"), "w"))
def q(v, ps=(0, 10, 50, 90, 100)):
    v = sorted(x for x in v if x is not None)
    return [round(v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))], 4) for p in ps] if v else None
for fam in ("v3.0", "v5.0"):
    for new in (False, True):
        G = [x for x in rows if x["fam"] == fam and x["new"] == new]
        print(f"== {fam} {'new' if new else 'old'}: {len(G)} bot buys; per pool p50 {q(list(collections.Counter((x['from'], x['off']) for x in G).values()), (50,))}")
        for rk in (0, 1, 2, 3, 5, 10):
            H = [x for x in G if x["rank"] == rk]
            if not H: continue
            print(f"  rank {rk:2d} n {len(H):4d} off {q([x['off'] for x in H])} gap {q([x['gap'] for x in H])} eth {q([x['eth'] for x in H], (10, 50, 90))} "
                  f"mo/launch {q([x['mo_launch'] for x in H], (0, 50, 100))} mo/now {q([x['mo_now'] for x in H], (0, 50, 100))} sell_after {q([x['sell_after'] for x in H], (10, 50, 90))} "
                  f"sold {sum(1 for x in H if x['sell_after'] is not None)}")
        print("  ranks per pool:", q([max(x["rank"] for x in G if x["from"] and True) for _ in [0]] if G else [], (50,)))
