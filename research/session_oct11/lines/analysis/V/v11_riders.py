"""Who else rides C-1 pools after the bot's first buy (fetched txs only: census + v07/v09). Per non-bot, non-launch wallet: pools, buy
offset after the trigger, size, its sells (when fetched), and the pull timing in its pools."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
crowd = {t["from"] for t in T.values() if t.get("to") == BOT}
W = C.defaultdict(lambda: {"pools": set(), "buys": [], "sells": [], "fp": C.Counter()})
for pid, r in rows.items():
    P = Pool(r, E[pid]); tb = R["trig"].get(pid)
    for x in P.sw:
        t = T.get(x[8])
        if t is None or t["to"] == BOT or t["from"] in crowd or t["from"] == r["launch"]["from"]: continue
        w = W[t["from"]]; w["pools"].add(pid); w["fp"][f"{t['to'][:10]}:{t['selector']}:{t['calldata_len']}"] += 1
        rel = (x[0] - tb[0]) if tb else None
        (w["buys"] if x[3] else w["sells"]).append((pid, x[0] - P.lb, rel, x[4] / 1e18, (P.first_pull - x[0]) if P.first_pull else None))
top = sorted(W.items(), key=lambda kv: -len(kv[1]["pools"]))[:15]
for a, w in top:
    b = w["buys"]; s = w["sells"]
    aft = [x for x in b if x[2] is not None and x[2] >= 0]
    print(f"{a} pools {len(w['pools'])} buys {len(b)} (after trigger {len(aft)}; trig+ p10/50/90 {p3([x[2] for x in aft])}) size p10/50/90 {p3([x[3] for x in b])} sells {len(s)} fp {w['fp'].most_common(2)}")
json.dump({a: {"pools": sorted(w["pools"]), "buys": w["buys"], "sells": w["sells"]} for a, w in top}, open(os.path.join(V, "v11_riders.json"), "w"))
