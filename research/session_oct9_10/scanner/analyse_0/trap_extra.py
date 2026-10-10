"""Trap tests with the outsiders each family actually has: (vbot-other) any non-dust, non-decoy buy before the bot's first buy;
(fee100-2276) real-size (>= 0.0002 / >= 0.001 ETH) non-crowd buys before the first crowd buy, among pools the crowd did reach;
(pm-init-500) the 9.5e-5 ETH sniper 0xe9d83e95 before the crowd vs pools without it. Measures: pull within N blocks of the outsider's
buy / of the first scheduled buy, and the pull's offset."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
out = {}
def load(i): return [json.loads(l) for l in open(os.path.join(HERE, f"pools_{i}.jsonl"))]
def pull_stats(rs, ref_fn, Ns=(5, 10, 20, 50, 100)):
    d = []
    for r in rs:
        ref = ref_fn(r)
        if ref is None: continue
        d.append((r["pull"]["off"] - ref) if r.get("pull") else None)
    n = len(d)
    return {"n": n, **{f"pulled_within_{N}": round(sum(1 for x in d if x is not None and x <= N) / max(1, n), 3) for N in Ns},
            "delay_p10_50_90": q([x for x in d if x is not None], (.1, .5, .9)), "never_3000": sum(1 for x in d if x is None)}
# vbot-other
R = [r for r in load(1) if r["sub"] in ("v3.0", "v5.0")]
w = [r for r in R if any(o["cls"] in ("other", "unknown") for o in r["before_sched"]) and r["sched"]]
wo = [r for r in R if not any(o["cls"] in ("other", "unknown") for o in r["before_sched"]) and r["sched"]]
fo = lambda r: next(o["off"] for o in r["before_sched"] if o["cls"] in ("other", "unknown"))
out["vbot-other"] = {"with_outsider": {"from_outsider": pull_stats(w, fo), "from_bot_buy": pull_stats(w, lambda r: r["sched"]["off"]),
                                       "pulled_before_bot_buy": sum(1 for r in w if r.get("pull") and r["pull"]["after_sched"] < 0),
                                       "outsider_eth": q([next(o["eth"] for o in r["before_sched"] if o["cls"] in ("other", "unknown")) for r in w], (0, .5, 1))},
                     "without": {"from_bot_buy": pull_stats(wo, lambda r: r["sched"]["off"])}}
# fee100-2276: pools the crowd reached
R = [r for r in load(2) if r["sched"]]
for thr in (0.0002, 0.001):
    w = [r for r in R if any(o["cls"] == "other" and o["eth"] >= thr for o in r["before_sched"])]
    wo = [r for r in R if not any(o["cls"] in ("other", "unknown", "vbot_decoy") and o["eth"] >= 0.0002 for o in r["before_sched"])]
    out[f"fee100-2276|outsider>={thr}"] = {"with": {"from_outsider": pull_stats(w, lambda r: next(o["off"] for o in r["before_sched"] if o["cls"] == "other" and o["eth"] >= thr)),
                                                    "from_crowd1": pull_stats(w, lambda r: r["sched"]["off"]),
                                                    "outsider_eth": q([max(o["eth"] for o in r["before_sched"] if o["cls"] == "other") for r in w], (0, .5, .9, 1))},
                                           "without": {"from_crowd1": pull_stats(wo, lambda r: r["sched"]["off"])}}
# pm-init-500: the sniper
R = [r for r in load(3) if r["sched"]]
SN = "0xe9d83e95b2248d8b33d63583762bd7f7465ddb28"
w = [r for r in R if any(o["from"] == SN for o in r["before_sched"])]
wo = [r for r in R if not any(o["cls"] in ("other", "unknown") for o in r["before_sched"])]
out["pm-init-500|sniper"] = {"with": {"from_outsider": pull_stats(w, lambda r: next(o["off"] for o in r["before_sched"] if o["from"] == SN), (50, 100, 150, 200)),
                                      "from_crowd1": pull_stats(w, lambda r: r["sched"]["off"], (50, 100, 150, 200))},
                             "without": {"from_crowd1": pull_stats(wo, lambda r: r["sched"]["off"], (50, 100, 150, 200))}}
json.dump(out, open(os.path.join(HERE, "trap_extra.json"), "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v))
