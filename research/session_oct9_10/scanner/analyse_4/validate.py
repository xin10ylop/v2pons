#!/usr/bin/env python3
"""Validate the pricer on our relay's real round trips in the census (v2.433 pools since Oct 10 09:07 and operator A):
replay our buy at its real block and size, our sell at its real block, compare with the chain's realized gross return."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ana import *   # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = [pid for pid, p in P.items() if p["known"] in ("vbot-v2.433", "operator-A")]
E = load_events(set(pids))
rows = []
for pid in pids:
    pl = Pool(P[pid], E.get(pid), T, M)
    rb = [x for x in pl.seq if x["relay"] and x["buy"]]
    rs = [x for x in pl.seq if x["relay"] and not x["buy"]]
    if len(rb) != 1 or len(rs) != 1: continue
    b, s = rb[0], rs[0]
    real = (s["eth"] - b["eth"]) / b["eth"]
    # last in its block?
    last = all((x["bn"], x["li"]) <= (b["bn"], b["li"]) for x in pl.seq if x["bn"] == b["bn"])
    first_in_S = all((x["bn"], x["li"]) >= (s["bn"], s["li"]) for x in pl.seq if x["bn"] == s["bn"])
    t = pl.trade(b["bn"], s["bn"], stake=b["eth"], minout_check=vbot_minout)
    if t.get("gross") is None: continue
    rows.append({"pid": pid, "known": P[pid]["known"], "B": b["bn"] - pl.b0, "S": s["bn"] - pl.b0, "stake": b["eth"] / 1e18, "real": real, "replay": t["gross"],
                 "err": t["gross"] - real, "last_in_B": last, "first_in_S": first_in_S})
print("pools with one relay round trip:", len(rows), collections.Counter(r["known"] for r in rows))
for k in ("vbot-v2.433", "operator-A"):
    rr = [r for r in rows if r["known"] == k]
    if not rr: continue
    e = [abs(r["err"]) for r in rr]
    clean = [r for r in rr if r["last_in_B"] and r["first_in_S"]]
    print(k, "n", len(rr), "real mean %.4f median %.4f | replay mean %.4f median %.4f | |err| median %.2e p90 %.2e max %.2e" % (
        st.mean(r["real"] for r in rr), st.median(r["real"] for r in rr), st.mean(r["replay"] for r in rr), st.median(r["replay"] for r in rr),
        st.median(e), sorted(e)[int(0.9 * (len(e) - 1))], max(e)))
    if clean:
        ec = [abs(r["err"]) for r in clean]
        print("   clean (our buy last in B, our sell first in S): n", len(clean), "|err| median %.2e max %.2e" % (st.median(ec), max(ec)))
    print("   stakes", collections.Counter(round(r["stake"], 5) for r in rr).most_common(4), "B", collections.Counter(r["B"] for r in rr).most_common(4))
    for r in sorted(rr, key=lambda r: -abs(r["err"]))[:5]:
        print("   worst", r)
json.dump(rows, open(os.path.join(HERE, "validate.json"), "w"), indent=0)
