#!/usr/bin/env python3
"""line_adapt trap: every v3.0/v5.0 pool of the 24 h with an outsider buy (not the bot's router, not the 2e-6 dust bot) before the bot's first buy:
the outsider's offset and size vs the operator's reaction (pulled before any bot buy / pulled at bot+2..+4 / no reaction), by regime
(old: launches before 04:17 UTC Oct 11; new: from 04:17). -> trap_offsets.json, printed table."""
import os, json, time, collections
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
F = json.load(open(os.path.join(D, "facts.json")))
CUT = 1791642747 + 0  # placeholder, replaced below
CUT = int(time.mktime(time.strptime("2026-10-11 04:17:00", "%Y-%m-%d %H:%M:%S"))) - time.timezone
rows = []
for f in F:
    if not f["outsider_pre"]: continue
    o = f["outsider_pre"][0]
    if f["early_pull"]: react = "pulled_before_bot"
    elif f["bot_off"] is not None and f["pull_off"] is not None and f["pull_off"] - f["bot_off"] <= 4: react = "pull_at_bot+%d" % (f["pull_off"] - f["bot_off"])
    elif f["bot_off"] is not None and f["pull_off"] is not None and f["pull_off"] - f["bot_off"] <= 20: react = "pull_at_bot+5..20"
    else: react = "none"
    rows.append({"t": time.strftime("%m-%d %H:%M:%S", time.gmtime(f["ts0"])), "fam": f["fam"], "pid": f["pid"], "regime": "new" if f["ts0"] >= CUT else "old",
                 "out_off": o[0], "out_eth": o[1], "out_from": o[2], "n_out": len(f["outsider_pre"]), "bot_off": f["bot_off"], "pull_off": f["pull_off"], "react": react})
json.dump(rows, open(os.path.join(HERE, "trap_offsets.json"), "w"), indent=0)
tab = collections.defaultdict(collections.Counter)
for r in rows: tab[(r["fam"], r["regime"], r["out_off"])][r["react"]] += 1
for k in sorted(tab): print(k, dict(tab[k]))
print("gap bot - outsider (old regime) vs reaction:")
g = collections.defaultdict(collections.Counter)
for r in rows:
    if r["regime"] == "old" and r["bot_off"] is not None: g[r["bot_off"] - r["out_off"]][r["react"]] += 1
for k in sorted(g): print("  gap", k, dict(g[k]))
print("outsider senders:", collections.Counter((r["out_from"], r["regime"]) for r in rows))
for r in rows:
    if r["react"] == "none" or r["regime"] == "new": print("  ", r)
