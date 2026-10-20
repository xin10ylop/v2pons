#!/usr/bin/env python3
"""line_adapt: who trades in the v3.0/v5.0 pools. Bot wallets = every wallet that bought through the bot router (c1120e3d) in any pool.
Every other buyer/seller: by (from, to, selector), its count, sizes, offsets (relative to the launch and to the pool's first bot buy), by regime.
-> actors.json"""
import os, json, time, collections
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
NEW_FROM = int(time.mktime(time.strptime("2026-10-11 04:22:19", "%Y-%m-%d %H:%M:%S"))) - time.timezone
R = [r for r in json.load(open(os.path.join(D, "rec.json"))) if r["complete"]]
botw = {s["from"] for r in R for s in r["swaps"] if s["bot"]}
launchers = {r["from"] for r in R}
print("bot wallets", len(botw), "launch wallets", len(launchers), "overlap", len(botw & launchers))
miss = sum(1 for r in R for s in r["swaps"] if s["to"] is None); print("swaps without tx", miss)
A = collections.defaultdict(lambda: {"n": 0, "pools": set(), "eth": [], "off": [], "rel_bot": [], "side": collections.Counter(), "fam": collections.Counter(), "reg": collections.Counter()})
for r in R:
    fb = next((s for s in r["swaps"] if s["bot"] and s["side"] == "B"), None)
    for s in r["swaps"]:
        if s["from"] in botw: continue
        k = (s["from"], s["to"], s["sel"])
        a = A[k]; a["n"] += 1; a["pools"].add(r["pid"]); a["eth"].append(abs(s["a0"]) / 1e18); a["off"].append(s["off"]); a["side"][s["side"]] += 1
        a["rel_bot"].append(s["off"] - fb["off"] if fb else None); a["fam"][r["fam"]] += 1; a["reg"]["new" if r["ts0"] >= NEW_FROM else "old"] += 1
out = []
for k, a in sorted(A.items(), key=lambda kv: -kv[1]["n"]):
    e = sorted(a["eth"]); o = sorted(a["off"]); rb = sorted(x for x in a["rel_bot"] if x is not None)
    out.append({"from": k[0], "to": k[1], "sel": k[2], "n": a["n"], "pools": len(a["pools"]), "side": dict(a["side"]), "fam": dict(a["fam"]), "reg": dict(a["reg"]),
                "eth_min_med_max": [e[0], e[len(e) // 2], e[-1]], "off_min_med_max": [o[0], o[len(o) // 2], o[-1]],
                "rel_bot_min_med_max": [rb[0], rb[len(rb) // 2], rb[-1]] if rb else None})
json.dump(out, open(os.path.join(HERE, "actors.json"), "w"), indent=0)
for x in out[:40]: print(x)
