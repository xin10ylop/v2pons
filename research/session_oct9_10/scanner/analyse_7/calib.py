"""calibration of the pricer on the controls: v2.433 front (live window, dropped/not dropped, by 6 h) and operator A follow"""
import sys, os, json, collections, statistics as st, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
rows = json.load(open(os.path.join(HERE, "rows.json")))
P = load_pools()
R = rows["control:vbot-v2.433"]
ts = lambda s: int(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp())
live_a, live_b = ts("2026-10-10 09:07"), ts("2026-10-10 11:40")
out = {}
relay_pools = set()
E = load_events(set(r["pid"] for r in R))
for r in R:
    if any(s["sender"] == RELAY for s in E[r["pid"]]["swaps"]): relay_pools.add(r["pid"])
out["v2433_all"] = summarize([r["front"] for r in R])
out["v2433_live_window"] = summarize([r["front"] for r in R if live_a <= r["ts"] <= live_b])
out["v2433_relay_traded_pools"] = summarize([r["front"] for r in R if r["pid"] in relay_pools])
out["v2433_not_dropped"] = summarize([r["front"] for r in R if not r["front"].get("dropped")])
out["v2433_bot_buy_dropped"] = summarize([r["front"] for r in R if r["front"].get("dropped")])
# what sits ahead of the bot's buy when it is dropped
ah = collections.Counter(); ah_eth = []
for r in R:
    if r["front"].get("dropped"):
        for o in r["outsiders"]: ah[(o[2], o[3][:10] if o[3] else None)] += 1
        ah_eth.append(r.get("cap", {}).get("eth_ahead_actual"))
out["dropped_eth_ahead_p10_50_90"] = q(ah_eth)
# eth ahead (actual chain, non-relay) of the bot buy: all pools
out["eth_ahead_all_p10_50_90"] = q([r.get("cap", {}).get("eth_ahead_actual") for r in R if r.get("cap")])
by6 = collections.defaultdict(list)
for r in R:
    h = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc); by6[h.strftime("%m-%d ") + "%02dh" % (h.hour // 6 * 6)].append(r["front"])
out["v2433_by_6h"] = {k: {kk: v[kk] for kk in ("n", "mean", "median", "win")} for k, v in ((k, summarize(v)) for k, v in sorted(by6.items()))}
# the pricer against the live record (front_audit/full_audit.json): our real relay trades, priced from the chain's own swaps
fa = "/home/user/v2pons/research/session_oct9_10/front_audit/full_audit.json"
if os.path.exists(fa):
    A = json.load(open(fa))
    out["live_audit_file_keys"] = list(A.keys())[:20] if isinstance(A, dict) else type(A).__name__
out["opA_follow"] = summarize([r["follow"] for r in rows["control:operator-A"] if r["follow"]])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v)[:400])
