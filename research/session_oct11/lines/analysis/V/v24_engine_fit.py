"""Engine-fit numbers for the follow rule T+2 / hold 60: the trigger's offset after the launch against TRIGGER_MAX_BLOCKS (150 default),
the bot's first-buy size against MIN_TRIGGER_ETH, how many trades the one position slot loses when launches bunch (a trade holds the
slot from the trigger to its sell at T+62), the distribution's tail (top 5% share, trimmed mean), and the per-trade $ at $15."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
g = {x["pid"]: x for x in R["grid"]["2|60"]}
offs = [R["trig"][p][0] - rows[p]["launch_block"] for p in R["trig"]]
print(f"trigger offset after launch: p10/50/90 {p3(offs)}; max {max(offs)}; > 150 (engine default TRIGGER_MAX_BLOCKS): {sum(1 for o in offs if o > 150)}/{len(offs)} ({sum(1 for o in offs if o > 150)/len(offs):.0%}); > 300: {sum(1 for o in offs if o > 300)}")
sz = [R["trig"][p][4] / 1e18 for p in R["trig"]]
print(f"bot first-buy size ETH: min {min(sz):.5f} p10/50/90 {p3(sz)}; below 0.005 (census 'real buy'): {sum(1 for s in sz if s < 0.005)}; below 0.0002 (engine MIN_TRIGGER_ETH): {sum(1 for s in sz if s < 0.0002)}")
# one slot: process triggers in time order; a trade occupies [T, T+62]
ev = sorted((R["trig"][p][0], p) for p in R["trig"]); busy_until = -1; taken = []; lost = []
for T, p in ev:
    if T <= busy_until: lost.append(p); continue
    taken.append(p); busy_until = T + 62
rt = lambda p: -1.0 if g[p]["pulled_le"] else g[p]["ret"]
xs = [rt(p) for p in taken]
print(f"one position slot: {len(taken)} trades taken, {len(lost)} lost to an open position ({len(lost)/len(ev):.1%}); taken mean {sum(xs)/len(xs):+.4f}")
allr = sorted(rt(p) for p in R["trig"]); n = len(allr); k = int(n * 0.95)
tot = sum(allr); top = sum(allr[k:])
print(f"tail: top 5% of trades ({n-k}) carry {top/tot:.0%} of the summed return; mean without them {sum(allr[:k])/k:+.4f}; returns > +100%: {sum(1 for v in allr if v > 1)}; max {max(allr):+.2f}")
usd = [v * 15 for v in allr]
print(f"$ per trade at $15: mean {sum(usd)/n:+.2f}, median {pct(usd,0.5):+.2f}; per day at {n/7:.1f} trades: {sum(usd)/7:+.0f}")
