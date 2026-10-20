"""Who buys ahead of the volume bot's buy in v2.433 pools (by router and wallet): sizes, offsets, period, and whether they sell
into the bot's buy (a copy of our front)."""
import sys, os, collections, statistics as st, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse as A
key = A.CONTROLS[0]
vbot = lambda s: s["txr"] is not None and s["txr"]["to"] == A.VBOT_ROUTER and s["txr"]["selector"] == "c1120e3d"
pids = A.fam_pids(key); ev = A.load_events(set(pids))
g = collections.defaultdict(list)
for pid in pids:
    v = A.build(pid, ev)
    buys = [s for s in v["swaps"] if s["a0"] < 0]
    sc = next((s for s in buys if vbot(s)), None)
    if not sc: continue
    for s in buys:
        if (s["bn"], s["li"]) >= (sc["bn"], sc["li"]): break
        t = s["txr"]; k = (t["to"] if t else "?", t["selector"] if t else "?", s["sender"])
        # does the same tx sender sell later (within 3000)? we know `from` only for the first 8 swaps
        sells = [x for x in v["swaps"] if x["a0"] > 0 and x["txr"] and t and x["txr"]["from"] == t["from"]]
        g[k].append((v["p"]["launch_ts"], s["bn"] - v["b0"], -s["a0"], t["from"] if t else "?", (sells[0]["bn"] - sc["bn"]) if sells else None, t["calldata_len"] if t else None))
for k, rs in sorted(g.items(), key=lambda kv: -len(kv[1]))[:10]:
    ts = sorted(r[0] for r in rs)
    f = lambda x: datetime.datetime.fromtimestamp(x, datetime.timezone.utc).strftime("%m-%d %H:%M")
    sz = [r[2] for r in rs]; off = [r[1] for r in rs]; sl = [r[4] for r in rs if r[4] is not None]
    print(k, "n", len(rs), "wallets", len(set(r[3] for r in rs)), "first", f(ts[0]), "last", f(ts[-1]), "size p10/50/90", [round(x/1e18, 6) for x in A.pct(sz)], "offset", A.pct(off),
          "sells after bot buy (blocks) n", len(sl), A.pct(sl), "calldata", collections.Counter(r[5] for r in rs).most_common(2))

print("\nper hour (Oct 10 from 12:00): pools, and per router: pools with a buy ahead of the bot, median size, max size; wallets")
H = collections.defaultdict(lambda: collections.defaultdict(list))
for k, rs in g.items():
    for r in rs:
        h = datetime.datetime.fromtimestamp(r[0], datetime.timezone.utc).strftime("%m-%d %H")
        H[h][k[0][:10]].append(r)
for h in sorted(H):
    if h < "10-10 12": continue
    print(h, {r: (len(x), round(st.median(y[2] for y in x)/1e18, 6), round(max(y[2] for y in x)/1e18, 6), len(set(y[3] for y in x))) for r, x in H[h].items()})
