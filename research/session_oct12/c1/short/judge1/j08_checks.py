"""Judge 1: small checks. (1) the holder-regime CI at max_blocks 100, hold 30, with more resamples and other seeds; (2) the reaction lags in
the pools max_blocks 100 trades (T <= 100); (3) $13 (0.0052 ETH at $2,500) for hold 30; (4) our real sells' landing lag (send at buy + hold)."""
from j02_sim import *
pools, head = load_pools(); line = [p for p in pools if p["shape"] == "line"]; stake = 2 * 10 ** 15
HOLDER = ("ours", "holder-pre", "holder-early", "holder-later", "bd13")
for mb in (100, 400):
    rows = run(line, stake, mb); A = [r for r in rows if r["reg"] in HOLDER]
    for ex in ("hold 25", "hold 30"):
        v = [usd(r, ex, stake) for r in A]
        print(f"(1) mb {mb} {ex} holder regime n {len(v)} mean {sum(v) / len(v):+.4f}; 95% CI seeds 1-3 x 50,000: " + "; ".join(f"[{boot(v, 50000, s)[0]:+.4f}, {boot(v, 50000, s)[1]:+.4f}]" for s in (1, 2, 3)))
R = json.load(open(JD("j04_reactions.json")))
lag100 = sorted((r["lag"], r["pid"], r["who"]) for r in R["held"] if r["T"] is not None and r["T"] <= 100 and r["buy_vs_T"] is not None and 0 <= r["buy_vs_T"] <= 150)
print(f"(2) holders bought T..T+150 in pools with T <= 100, pulled within 600 blocks: lags {[x[0] for x in lag100]}")
print(f"    every triggered pool with T <= 100: earliest pulls after our would-be buy {sorted(x[0] for x in R['triggered'] if x[1] <= 100 and x[0] is not None)[:6]}")
for mb in (400, 100):
    st = 52 * 10 ** 14; rows = run(line, st, mb); A = [r for r in rows if r["reg"] in HOLDER]
    for nm, S in (("holder", A), ("all", rows)):
        v = [usd(r, "hold 30", st) for r in S]; lo, hi = boot(v)
        print(f"(3) $13 (0.0052 ETH) mb {mb} hold 30 {nm}: {sum(v) / len(v):+.3f} [{lo:+.3f}, {hi:+.3f}] fills {sum(r['fill'] for r in S)}/{len(S)}")
# (4) our sells: landing vs buy
O = json.load(open(J("c04_ours.json")))
D = json.load(open(JD("j01_pools.json")))
for p in D["pools"]:
    o = [s for s in p["sw"] if s["cls"] == "ours"]
    if len(o) == 2: print(f"(4) {p['pid'][:10]} our buy block {o[0]['bn']} (T+{o[0]['off'] - p['T']}) sell block {o[1]['bn']}: sell landed buy+{o[1]['bn'] - o[0]['bn']} (tx index {o[1]['ti']})")
for t in O:
    if t.get("c1"): print(f"(4) reverted {t['input'][:10]} {t['c1'][:10]} block {t['block']}")
