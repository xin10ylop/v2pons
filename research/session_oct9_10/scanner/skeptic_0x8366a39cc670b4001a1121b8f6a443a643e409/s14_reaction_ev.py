"""The claimed rules priced with the operator's observed reaction to an outsider buy: our buy at block B is an outsider buy, so a pull is
added at B + d, d drawn from the observed delays (census: first outsider buy >= 1e-4 per pool within add+590, full tx coverage; fresh:
every outsider buy >= 0.0003 after the census). None = no reaction seen (the pool's own pull stands)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_s import *
F = load_families(); pids = F[KEY]["pids"]; P = load_pools(); E = load_events(set(pids))
R = {r["pid"]: r for r in json.load(open(os.path.join(HERE, "timeline.json")))}
census_d = [e["delay"] for e in json.load(open(os.path.join(HERE, "reaction.json")))["thr_0.0001"]["events"]]
fresh = json.load(open(os.path.join(HERE, "fresh_summary.json")))["rows"]
fresh_d = []
for r in fresh:
    o = [x for x in r["outsider_buys"] if x[1] >= 0.0003 and (r["pull"] is None or x[0] <= r["pull"])]
    if o: fresh_d.append(r["pull"] - o[0][0] if r["pull"] is not None else None)
print("census delays", census_d); print("fresh delays", fresh_d)
D = census_d + fresh_d
rules = {"ride +1->+180": lambda a, r: (a + 1, a + 180), "follow crowd1+1 hold 100": lambda a, r: (a + r["crowd1"] + 1, a + r["crowd1"] + 101),
         "front +1 -> crowd1+1 (deadline +220)": lambda a, r: (a + 1, a + min(r["crowd1"] + 1, 220))}
out = {"census_delays": census_d, "fresh_delays": fresh_d}
for name, f in rules.items():
    for lab, dl in (("no reaction (the claim)", [None]), ("observed delays, census+fresh n=%d" % len(D), D), ("4-5 block reactions only, %d of %d" % (sum(1 for d in D if d is not None and d <= 5), len(D)), [4 if (d is not None and d <= 5) else None for d in D])):
        rs = []
        for p in pids:
            pl = Pool(P[p], E[p]); B, S = f(pl.add, R[p]); real = pl.pull
            for d in dl:
                pl.pull = real if d is None else (min(real, B + d) if real is not None else B + d)
                rs.append(pl.trade(B, S)); pl.pull = real
        s = summ(rs); s["usd_day"] = round(s["mean"] * 15 * 96, 1); s["pulled_share"] = round(s["pulled"] / s["n"], 3)
        out[f"{name} | {lab}"] = s; print(name, "|", lab, s)
# break-even reaction probability: p * (1 + g) = (1 - p) * m  ->  p = m / (1 + m) with m the no-reaction mean
json.dump(out, open(os.path.join(HERE, "reaction_ev.json"), "w"), indent=1)
