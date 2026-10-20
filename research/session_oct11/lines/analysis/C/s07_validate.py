"""Check the simulators: for every swap of the studied pools, predict its output from the state just before it (state synced to the
real events) and compare with the event's output. Also check that V3 synced prices agree with the re-simulated ones."""
import sys, os, pickle, copy, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
err = defaultdict(list); bad = defaultdict(int)
for name, rs in FP.items():
    for r in rs[:300]:
        o = E[r["pool"]]; sim = make_sim(r); qs = r["quote_side"]
        for e in o["ev"]:
            if e[0] == "s" and sim.ok():
                c = copy.deepcopy(sim)
                if r["dex"] == "v3":
                    dq, dt = (e[7], e[8]) if qs == 0 else (e[8], e[7])
                    if dq > 0: pred, real = c.buy(dq), -dt
                    else: pred, real = c.sell(dt), -dq
                    if real > 0:
                        err[(name, "v3", "B" if dq > 0 else "S")].append(abs(pred / real - 1))
                        # price check
                        err[(name, "v3", "sqrtP")].append(abs(c.s * Q96 / e[9] - 1))
                else:
                    qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
                    if qin > 0 and tout > 0: pred, real, k = c.buy(qin), tout, "B"
                    elif tin > 0: pred, real, k = c.sell(tin), qout, "S"
                    else: continue
                    if real > 0: err[(name, "v2", k)].append(abs(pred / real - 1))
            sim.apply(e)
for k, v in sorted(err.items()):
    v = sorted(v)
    print(k, "n", len(v), "median rel err %.2e" % v[len(v)//2], "p90 %.2e" % v[int(.9*len(v))], "share >1e-3: %.3f" % (sum(1 for x in v if x > 1e-3) / len(v)))
