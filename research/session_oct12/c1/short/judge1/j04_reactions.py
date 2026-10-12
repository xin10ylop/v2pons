"""Judge 1: every known reaction pull, and each exit's margin to it.
(i) positions held into a pull: an outside buy of >= 0.001 ETH (recurring/oneoff) or ours, not sold before the pull, pull within 600 blocks of
    the buy; the lag pull - buy, the pool age at the pull, the router's last buy before the pull (from the holder's buy), where the buy sat vs T.
(ii) every triggered pool (engine T <= 400, the line's shape): the pull measured from our would-be buy at T+2; the earliest ones.
(iii) margins: exit landing block (from our buy; lag 1-2 seen, 3 as stress) vs each reaction lag; and on the pool-age axis, the landing
    (T + 2 + exit) vs the earliest pull age of a reaction pool.
Writes j04_reactions.json."""
from j02_sim import *
pools, head = load_pools()
OUTC = ("recurring", "oneoff")
R = []
for p in pools:
    if p["pull"] is None or p["shape"] == "other": continue
    k0, T = engine_T(dict(p, sw=[s for s in p["sw"] if s["cls"] != "ours"]), 400)
    if k0 is None: T = None
    pb = p["pullpos"][0]
    for s in p["sw"]:
        if not s["buy"] or (s["cls"] not in OUTC and s["cls"] != "ours"): continue
        if s["cls"] in OUTC and s["eth"] < 0.001: continue
        if (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        sold = any((not x["buy"]) and x.get("from") == s.get("from") and (s["bn"], s["li"]) < (x["bn"], x["li"]) < tuple(p["pullpos"]) for x in p["sw"])
        if sold: continue
        lag = pb - s["bn"]
        if lag > 600: continue
        rb = [x for x in p["sw"] if x["buy"] and x["cls"] == "router" and (s["bn"], s["li"]) < (x["bn"], x["li"]) < tuple(p["pullpos"])]
        R.append({"pid": p["pid"][:10], "ts": p["ts"], "who": "ours" if s["cls"] == "ours" else s["from"][:10], "eth": s["eth"], "buy_off": s["off"], "T": T,
                  "buy_vs_T": None if T is None else s["off"] - T, "pull_off": p["pull"], "lag": lag, "last_router_after_buy": (rb[-1]["bn"] - s["bn"]) if rb else None,
                  "router_buys_after": len(rb), "shape": p["shape"]})
# one row per (pool, holder): the first held buy of each holder
seen = set(); R1 = []
for r in sorted(R, key=lambda r: (r["pid"], r["who"], -r["lag"])):
    k = (r["pid"], r["who"])
    if k in seen: continue
    seen.add(k); R1.append(r)
R1.sort(key=lambda r: r["lag"])
print("(i) positions held into a pull within 600 blocks of the buy (first held buy per holder and pool), shortest lags first:")
print("   lag  age@pull  buy@T+   T   router after buy (n, last@)   who         ETH     pool       launched")
for r in R1[:40]:
    print(f"  {r['lag']:4d}  L+{r['pull_off']:4d}   {str(r['buy_vs_T']):>5s}  {str(r['T']):>4s}   {r['router_buys_after']:3d}, {str(r['last_router_after_buy']):>4s}             {r['who']:10s}  {r['eth']:.4f}  {r['pid']}  {utc(r['ts'])} {r['shape']}")
post = [r for r in R1 if r["buy_vs_T"] is not None and 0 <= r["buy_vs_T"] <= 150]
pre = [r for r in R1 if r["buy_vs_T"] is not None and r["buy_vs_T"] < 0]
print(f"\n  bought at T..T+150 (as our entry): {len(post)}; lags sorted: {sorted(r['lag'] for r in post)}")
print(f"  bought before T: {len(pre)}; pull from T+2 (our buy): {sorted((r['pull_off'] - r['T'] - 2, r['pid']) for r in pre)}")
# (ii) every triggered pool: the pull vs our would-be buy at T+2
TP = []
for p in pools:
    if p["shape"] != "line": continue
    k0, T = engine_T(dict(p, sw=[s for s in p["sw"] if s["cls"] != "ours"]), 400)
    if k0 is None: continue
    TP.append((None if p["pull"] is None else p["pull"] - T - 2, T, p["pull"], p["pid"][:10], utc(p["ts"])))
TP.sort(key=lambda x: (x[0] is None, x[0]))
print(f"\n(ii) triggered line pools {len(TP)}: the 12 earliest pulls after our would-be buy (T+2):")
for x in TP[:12]: print(f"   buy+{x[0]:4d}  T +{x[1]:3d}  pull L+{x[2]}  {x[3]} {x[4]}")
ages = sorted(p["pull"] for p in pools if p["pull"] is not None and p["shape"] == "line" and engine_T(dict(p, sw=[s for s in p["sw"] if s["cls"] != "ours"]), 400)[0] is not None)
print(f"   earliest pull age of a triggered pool: L+{ages[:8]}")
print(f"   pools with T > 100: {sum(1 for x in TP if x[1] > 100)} of {len(TP)}; T > 113 (hold 30 lands after L+147): {sum(1 for x in TP if x[1] > 113)}")
# (iii) margins
EX = [("hold 20", 20), ("hold 25", 25), ("hold 30", 30), ("hold 35", 35), ("tp 4%/6% cap 30 (no TP)", 30), ("tp 4%/6% cap 40 (no TP)", 40)]
lags = sorted(r["lag"] for r in post)
lags_all = sorted([r["lag"] for r in post] + [r["pull_off"] - r["T"] - 2 for r in pre])
print("\n(iii) margin = reaction lag - landing (from our buy). Landing = send + 1..2 (our 8 c1 sells: +1 once, +2 seven times); +3 as stress.")
print("     exit                      landing   min margin to post-T reactions (36 = ours)   to pre-T holders' pulls (from T+2)   reactions within landing+3")
for nm, n in EX:
    lmax = n + 2
    m_post = lags[0] - lmax; m_pre = min(r["pull_off"] - r["T"] - 2 for r in pre) - lmax
    within = sum(1 for x in lags_all if x <= lmax + 1)
    print(f"     {nm:26s} +{n + 1}..+{lmax}   {m_post:+4d} (next: {', '.join(f'{x - lmax:+d}' for x in lags[1:5])})            {m_pre:+4d}                              {within}")
json.dump({"held": R1, "triggered": TP}, open(JD("j04_reactions.json"), "w"))
