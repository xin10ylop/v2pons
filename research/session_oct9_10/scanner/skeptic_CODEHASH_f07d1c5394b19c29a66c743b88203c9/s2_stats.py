import json, collections, statistics as st, datetime
D=json.load(open("g3_raw.json")); G=D["pools"]; E=D["events"]; T=D["txs"]
def pct(xs):
    xs=sorted(xs); n=len(xs)
    return [xs[int(q*(n-1))] for q in (0.1,0.5,0.9)] if xs else None
rows=[]; buyers=collections.Counter(); pullfrom_is_launch=0; nsw=collections.Counter(); seller=collections.Counter()
deployers=collections.Counter(p["launch_from"] for p in G)
for p in G:
    e=E[p["pid"]]; lb=p["launch_block"]
    sw=e["swaps"]; pu=e["pulls"]
    nsw[len(sw)]+=1
    buys=[s for s in sw if s["a0"]<0]; sells=[s for s in sw if s["a0"]>0]
    for s in sw:
        t=T.get(s["tx"]); buyers[(t["from"] if t else None, "buy" if s["a0"]<0 else "sell")]+=1
    fb=buys[0] if buys else None
    pl=pu[0] if pu else None
    if pl:
        t=T.get(pl["tx"]); pullfrom_is_launch += (t and t["from"]==p["launch_from"])
    rows.append(dict(pid=p["pid"], lb=lb, ts=p["launch_ts"], fb_rel=fb and fb["bn"]-lb, fb_eth=fb and -fb["a0"]/1e18, pull_rel=pl and pl["bn"]-lb,
                     margin=(pl["bn"]-fb["bn"]) if (pl and fb) else None, nbuys=len(buys), nsells=len(sells), sqrt=p["sqrt_p0"], liq=p["liq_launch"],
                     value=p["launch_value_wei"], nonce=p["launch_nonce"], from_=p["launch_from"]))
print("n pools", len(G), "swaps-per-pool", dict(nsw))
print("swap tx from x side", buyers.most_common(10))
print("deployers", len(deployers), deployers.most_common(5))
print("nonce", collections.Counter(p["launch_nonce"] for p in G))
print("value", collections.Counter(p["launch_value_wei"] for p in G))
print("sqrt", collections.Counter(p["sqrt_p0"] for p in G), "liq", collections.Counter(p["liq_launch"] for p in G))
print("fee/ts", collections.Counter((p["fee"],p["tick_spacing"]) for p in G))
fb=[r["fb_rel"] for r in rows if r["fb_rel"] is not None]; print("first buy rel n", len(fb), "p10/50/90", pct(fb), collections.Counter(fb))
fe=[r["fb_eth"] for r in rows if r["fb_eth"] is not None]; print("first buy eth p10/50/90", pct(fe), "min", min(fe), "max", max(fe))
print("buy size histogram", collections.Counter(round(x,2) for x in fe).most_common(20))
pr=[r["pull_rel"] for r in rows if r["pull_rel"] is not None]; print("pull rel n", len(pr), pct(pr))
mg=[r["margin"] for r in rows if r["margin"] is not None]; print("margin n", len(mg), pct(mg), collections.Counter(mg))
print("pull from == launch wallet", pullfrom_is_launch)
print("no buy:", [ (r["pid"][:10], r["pull_rel"]) for r in rows if r["fb_rel"] is None])
print("pull before/without buy:", [(r["pid"][:10], r["fb_rel"], r["pull_rel"]) for r in rows if r["pull_rel"] is None or (r["fb_rel"] is not None and r["pull_rel"]<r["fb_rel"])])
ts=[p["launch_ts"] for p in G]; print("time", datetime.datetime.utcfromtimestamp(min(ts)), datetime.datetime.utcfromtimestamp(max(ts)))
gaps=sorted(b-a for a,b in zip(ts,ts[1:])); print("gaps s max", gaps[-5:], "median", st.median(gaps))
# time series
for r in rows[:3]+rows[-3:]: print(datetime.datetime.utcfromtimestamp(r["ts"]), r)
json.dump(rows, open("rows.json","w"))
