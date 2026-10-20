import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
for key in ["0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|3000|60|false", "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|10000|100|false", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|883131|200|true"]:
    pids = F[key]["pids"]; E = load_events(set(pids))
    c = collections.Counter(); tok = collections.Counter(); froms = collections.Counter(); pulls_by = collections.Counter(); liq = []
    for pid in pids:
        e = E.get(pid, {"swaps": [], "pulls": [], "adds": []}); p = P[pid]
        tok[p["token"]] += 1; froms[p["launch_from"]] += 1; liq.append(p["liq_launch"])
        for s in e["swaps"]:
            c["zero" if s["a0"] == 0 and s["a1"] == 0 else ("buy" if s["a0"] < 0 else "sell")] += 1
        for q in e["pulls"][:1]: pulls_by[(T.get(q["tx"], {}).get("from"), T.get(q["tx"], {}).get("selector"))] += 1
        tick_vs = [(a["lo"] > p["tick0"], a["hi"] < p["tick0"]) for a in e["adds"][:1]]
        c[("range_above_price", tuple(tick_vs))] += 1
    print(key); print("  swaps", dict(c)); print("  tokens distinct", len(tok), tok.most_common(4)); print("  launchers", froms.most_common(3)); print("  first pull by", pulls_by.most_common(4))
    print("  liq_launch zero/None", sum(1 for x in liq if not x), "of", len(liq))
    lbs = sorted(P[pid]["launch_block"] for pid in pids); print("  launch blocks", lbs[0], lbs[-1], "fees", collections.Counter(P[pid]["fee"] for pid in pids).most_common(3))
