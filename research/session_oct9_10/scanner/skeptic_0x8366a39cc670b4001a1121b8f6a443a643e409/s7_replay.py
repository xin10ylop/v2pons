import sys, os, random; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_s import *
F = load_families(); pids = F[KEY]["pids"]; P = load_pools(); E = load_events(set(pids))
R = {r["pid"]: r for r in json.load(open(os.path.join(HERE, "timeline.json")))}
pools = {p: Pool(P[p], E[p]) for p in pids}
errs = [pools[p].check() for p in pids]; print("replay check: max rel sqrt error per pool p50/p99/max", q(errs, (.5, .99, 1)))
out = {}
def run(name, f, sample):
    rs = []
    for p in sample:
        pl = pools[p]; r = R[p]; BS = f(pl, r)
        if BS: rs.append(pl.trade(*BS))
    out[name] = summ(rs); print(name, out[name])
random.seed(7); mine = sorted(random.sample(pids, 96)); late = pids[96:]
for lab, sample in (("all", pids), ("random96", mine), ("second_half", late)):
    print("==", lab)
    run(lab + "|ride +1->+180", lambda pl, r: (pl.add + 1, pl.add + 180), sample)
    run(lab + "|ride +1->+150", lambda pl, r: (pl.add + 1, pl.add + 150), sample)
    run(lab + "|ride +1->+220", lambda pl, r: (pl.add + 1, pl.add + 220), sample)
    run(lab + "|front +1 -> crowd1+1", lambda pl, r: (pl.add + 1, min(pl.add + r["crowd1"] + 1, pl.add + 220)), sample)
    run(lab + "|follow crowd1+1, hold 100", lambda pl, r: (pl.add + r["crowd1"] + 1, pl.add + r["crowd1"] + 101), sample)
    run(lab + "|literal front: +1 -> +20", lambda pl, r: (pl.add + 1, pl.add + 20), sample)
json.dump(out, open(os.path.join(HERE, "replay.json"), "w"), indent=1)
