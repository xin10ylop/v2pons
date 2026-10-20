"""How unusual are the post-census pools under the census distribution? Resample 17 census trades (T+2/H60) / census waves (ETH of buys
>= 0.01 by T+60) 100,000 times, all 7 days and the last 24 h only; the share of draws whose mean return / median wave is at or below the
post-census value."""
import pickle, random
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
g = {x["pid"]: (-1.0 if x["pulled_le"] else x["ret"]) for x in R["grid"]["2|60"]}
wave = {}
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid]); wave[pid] = sum(x[4] for x in P.sw if tb[0] < x[0] <= tb[0] + 60 and x[3] and x[4] >= 10**16) / 1e18
FR = [o for o in json.load(open(os.path.join(V, "fresh_replay.json"))) if "ret" in o]
fr_mean = sum(o["ret"] for o in FR) / len(FR); n = len(FR)
lines = open(os.path.join(V, "v19_fresh_timeline.out")).read()
import re
fw = [float(m.group(1)) for m in re.finditer(r"ETH by cuts \[[0-9.]+, ([0-9.]+),", lines)]
fw_med = pct(fw, 0.5)
random.seed(5)
for name, pool in (("all 7 days", list(g)), ("last 24 h", [p for p in g if day_of(rows[p]["launch_ts"]) == 6])):
    k1 = k2 = 0; N = 100_000
    for _ in range(N):
        s = random.choices(pool, k=n)
        k1 += sum(g[p] for p in s) / n <= fr_mean
        k2 += pct([wave[p] for p in s], 0.5) <= fw_med
    print(f"{name} (pool {len(pool)}): P(mean of {n} trades <= {fr_mean:+.4f}) = {k1/N:.4f}; P(median wave of {n} <= {fw_med:.3f} ETH) = {k2/N:.4f}")
