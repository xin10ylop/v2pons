"""Calibration of the pricer on the volume bot's v2.433 family: front by period and by the size bought ahead of the bot."""
import sys, os, json, collections, statistics as st, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse as A
key = A.CONTROLS[0]
vbot = lambda s: s["txr"] is not None and s["txr"]["to"] == A.VBOT_ROUTER and s["txr"]["selector"] == "c1120e3d"
pids = A.fam_pids(key); ev = A.load_events(set(pids))
V = [A.build(pid, ev) for pid in pids]
rows = []
for v in V:
    buys = [s for s in v["swaps"] if s["a0"] < 0 and not s["in_launch"]]
    v["sched"] = next((s for s in buys if vbot(s)), None)
    B = v["b0"] + 1
    if not v["sched"] or v["sched"]["bn"] <= B: continue
    S = v["sched"]["bn"] + 1
    r = A.trade(v, B, S, sched=v["sched"])
    ahead = sum(-s["a0"] for s in buys if (s["bn"], s["li"]) < (v["sched"]["bn"], v["sched"]["li"]))
    mo, _ = A.min_out_of(v["sched"])
    rows.append((v["p"]["launch_ts"], r["ret"], bool(r.get("dropped")), ahead, -v["sched"]["a0"], v["pull"] - v["b0"] if v["pull"] else None, v["sched"]["bn"] - v["b0"], v["n_relay"]))
def ts(h, m, d=10): return int(datetime.datetime(2026, 10, d, h, m, tzinfo=datetime.timezone.utc).timestamp())
def show(name, rs):
    if not rs: print(name, "none"); return
    v = [r[1] for r in rs]
    print("%-58s n %4d mean %+6.2f%% median %+6.2f%% win %3.0f%% dropped %3d ahead_p50 %.6f bot_p50 %.4f" % (name, len(v), 100*st.mean(v), 100*st.median(v), 100*sum(1 for a in v if a > 0)/len(v), sum(1 for r in rs if r[2]), st.median(r[3] for r in rs)/1e18, st.median(r[4] for r in rs)/1e18))
show("all", rows)
show("before Oct 10 09:07 (engine off)", [r for r in rows if r[0] < ts(9, 7)])
show("Oct 10 09:07-15:04", [r for r in rows if ts(9, 7) <= r[0] < ts(15, 4)])
show("after Oct 10 15:04 (decoy grew)", [r for r in rows if r[0] >= ts(15, 4)])
show("ahead < 0.0002 ETH", [r for r in rows if r[3] < 2e14])
show("ahead >= 0.0002 ETH", [r for r in rows if r[3] >= 2e14])
show("not dropped", [r for r in rows if not r[2]])
show("dropped", [r for r in rows if r[2]])
show("bot buy >= 0.17 ETH, not dropped", [r for r in rows if r[4] >= 0.17e18 and not r[2]])
# decoy size by hour
by = collections.defaultdict(list)
for r in rows: by[datetime.datetime.fromtimestamp(r[0], datetime.timezone.utc).strftime("%m-%d %H")].append(r)
print("hour      n  ahead_max_p50   dropped  mean")
for h in sorted(by):
    rs = by[h]; print(h, "%4d %.6f %4d %+6.2f%%" % (len(rs), st.median(r[3] for r in rs)/1e18, sum(1 for r in rs if r[2]), 100*st.mean(r[1] for r in rs)))
