"""who else buys the v2.433 pools before the volume bot's own buy (the control's outsiders): wallets/routers, offsets, sizes, first/last time,
and whether they sell into the bot's buy (a competing front bot)"""
import sys, os, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
R = rows["control:vbot-v2.433"]
P = load_pools(); T = load_txs()
pids = [r["pid"] for r in R]
E = load_events(set(pids))
agg = collections.defaultdict(lambda: {"pools": 0, "rel": [], "eth": [], "ts": [], "sell_after_bot": 0, "sell_rel_from_bot": []})
for r in R:
    if not r["sched"]: continue
    sb = r["sched"]; b0 = r["b0"]
    e = E[r["pid"]]
    seen = set()
    for o in r["outsiders"]:
        if o[1] < 0.0002: continue
        key = f"{o[2]}|{o[3]}"
        if key in seen: continue
        seen.add(key)
        a = agg[key]; a["pools"] += 1; a["rel"].append(o[0]); a["eth"].append(o[1]); a["ts"].append(r["ts"])
        # a sell by the same tx 'to' (router) after the bot's buy, within 10 blocks (sender of the swap = the router when it calls the PM)
        for s in e["swaps"]:
            if s["a0"] > 0 and s["bn"] >= b0 + sb["rel"] and s["bn"] <= b0 + sb["rel"] + 10:
                t = T.get(s["tx"])
                if (t and t["from"] == o[3]) or s["sender"] == o[2]:
                    a["sell_after_bot"] += 1; a["sell_rel_from_bot"].append(s["bn"] - b0 - sb["rel"]); break
out = {}
for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["pools"])[:8]:
    out[k] = {"pools": a["pools"], "rel_p10_50_90": q(a["rel"]), "eth_p10_50_90": q(a["eth"]), "first": dt.datetime.utcfromtimestamp(min(a["ts"])).isoformat(),
              "last": dt.datetime.utcfromtimestamp(max(a["ts"])).isoformat(), "sold_within_10_after_bot": a["sell_after_bot"],
              "sell_rel_from_bot": dict(collections.Counter(a["sell_rel_from_bot"]).most_common(5))}
json.dump(out, open(os.path.join(HERE, "competitor.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
