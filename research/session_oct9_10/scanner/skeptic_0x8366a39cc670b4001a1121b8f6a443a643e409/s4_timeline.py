import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
F = load_families(); pids = F[KEY]["pids"]; P = load_pools(); E = load_events(set(pids)); C = load_cache()
rows = []
for p in pids:
    pr = P[p]; e = E[p]; ad = e["adds"][0]; a = ad["bn"]; at = C[ad["tx"]]
    r = {"pid": p, "b0": pr["launch_block"], "ts": pr["launch_ts"], "add": a, "add_off": a - pr["launch_block"], "deployer": pr["launch_from"], "init_nonce": pr["launch_nonce"],
         "add_from": at["from"], "add_nonce": at["nonce"], "add_value": at["value"] / 1e18, "add_len": at["len"], "add_sel": at["sel"], "add_to": at["to"],
         "sqrt_p0": pr["sqrt_p0"], "tick0": pr["tick0"], "lo": ad["lo"], "hi": ad["hi"], "L": ad["dl"], "token": pr["token"],
         "full_range": ad["lo"] <= -887000, "one_sided": ad["hi"] < pr["tick0"]}
    sw = []
    for s in e["swaps"]:
        t = C.get(s["tx"]); cl = classify(t) if t else "nofetch"
        sw.append({"off": s["bn"] - a, "bn": s["bn"], "li": s["li"], "buy": s["a0"] < 0, "eth": abs(s["a0"]) / 1e18, "cls": cl, "from": t["from"] if t else None,
                   "to": t["to"] if t else s["sender"], "sel": t["sel"] if t else None, "len": t["len"] if t else None, "nonce": t["nonce"] if t else None})
    r["swaps"] = sw
    cb = [x for x in sw if x["cls"] == "crowd" and x["buy"]]
    r["crowd1"] = cb[0]["off"] if cb else None
    r["crowd1_eth"] = cb[0]["eth"] if cb else None
    r["crowd_sizes"] = [round(x["eth"], 8) for x in cb[:12]]
    cs = [x for x in sw if x["cls"] == "crowd" and not x["buy"]]
    r["crowd_sell1"] = cs[0]["off"] if cs else None; r["crowd_sell1_eth"] = cs[0]["eth"] if cs else None
    r["pull"] = (e["pulls"][0]["bn"] - a) if e["pulls"] else None
    if e["pulls"]:
        pt = C[e["pulls"][0]["tx"]]; r["pull_from"] = pt["from"]; r["pull_to"] = pt["to"]; r["pull_sel"] = pt["sel"]; r["pull_nonce"] = pt["nonce"]
        r["pull_full"] = -e["pulls"][0]["dl"] == ad["dl"]
    rows.append(r)
json.dump(rows, open(os.path.join(HERE, "timeline.json"), "w"))
n = len(rows)
print("n", n, "add_off q", q([r["add_off"] for r in rows], (0, .1, .5, .9, 1)))
print("add_from == deployer", sum(r["add_from"] == r["deployer"] for r in rows), "add_to", collections.Counter((r["add_to"], r["add_sel"], r["add_len"]) for r in rows))
print("init nonce", collections.Counter(r["init_nonce"] for r in rows), "add nonce", collections.Counter(r["add_nonce"] for r in rows))
print("add value", collections.Counter(round(r["add_value"], 4) for r in rows).most_common(12))
print("full range", sum(r["full_range"] for r in rows), "one sided", sum(r["one_sided"] for r in rows))
print("pairs", collections.Counter((r["sqrt_p0"], r["L"]) for r in rows).most_common(8))
print("crowd present", sum(r["crowd1"] is not None for r in rows), "crowd1 off", q([r["crowd1"] for r in rows], (0, .1, .5, .9, 1)))
print("crowd1 eth", collections.Counter(r["crowd1_eth"] for r in rows).most_common(6))
seqs = collections.Counter(tuple(r["crowd_sizes"][:6]) for r in rows); print("distinct first-6 crowd size sequences", len(seqs), seqs.most_common(3))
print("crowd sell1 off", q([r["crowd_sell1"] for r in rows], (0, .1, .5, .9, 1)), "n with crowd sell in fetched", sum(r["crowd_sell1"] is not None for r in rows))
pl = [r for r in rows if r["pull"] is not None]
print("pulled", len(pl), "pull off from add", sorted(r["pull"] for r in pl))
print("pull from == deployer", sum(r["pull_from"] == r["deployer"] for r in pl), collections.Counter((r["pull_to"], r["pull_sel"]) for r in pl), "full", sum(r["pull_full"] for r in pl))
print("pull nonce", collections.Counter(r["pull_nonce"] for r in pl))
