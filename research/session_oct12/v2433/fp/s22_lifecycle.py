"""The 2.4333 pool lifecycle across the window (all 91 pools): launch interval, the bot's first buy offset T and its buy count/ETH (s06 + s14),
and the pull (first ModifyLiquidity < 0, one OR-query over the 91 pool ids) - by 2-hour block, to show drift or none before the stop."""
import json, collections, time, statistics as S
from clusters import load
from common import R, PM, T_ML, W, sgn, p, load_jsonl
meta = json.load(open(p("s01_meta.json")))
rows = [r for r in load() if r["fam"].startswith("VB 2.4333")]; pid = {r["pid"]: r for r in rows}; tok = {r["c1"]: r["pid"] for r in rows}
ml = load_jsonl("s22_ml_cache.jsonl")
if not ml:
    ls = R.logs({"address": PM, "topics": [T_ML, [r["pid"] for r in rows]]}, rows[0]["b"], meta["head"])
    ml = [{"b": int(l["blockNumber"], 16), "pid": l["topics"][1], "dl": str(sgn(W(l["data"], 2)))} for l in ls]
    with open(p("s22_ml_cache.jsonl"), "w") as f: f.write("".join(json.dumps(x) + "\n" for x in ml))
pull = {}
for m in sorted(ml, key=lambda m: m["b"]):
    if int(m["dl"]) < 0 and m["pid"] not in pull: pull[m["pid"]] = m["b"] - pid[m["pid"]]["b"]
botbuy = {x["h"] for x in load_jsonl("s06_bot_transfers_cache.jsonl") if x["side"] == "to" and int(x["t1"], 16) != 0}
bot = collections.defaultdict(list)
for s in load_jsonl("s14_swaps_cache.jsonl"):
    if s["pid"] in pid and s["h"] in botbuy: bot[s["pid"]].append((s["b"] - pid[s["pid"]]["b"], -sgn(W(s["d"], 0)) / 1e18))
print("pools", len(rows), "pulled", len(pull), "never pulled", [time.strftime("%H:%M", time.gmtime(r["t"])) for r in rows if r["pid"] not in pull])
blocks = collections.defaultdict(list)
for i, r in enumerate(rows):
    blocks[int((r["t"] - rows[0]["t"]) // 7200)].append((i, r))
for k in sorted(blocks):
    v = blocks[k]
    gaps = [rows[i]["t"] - rows[i - 1]["t"] for i, _ in v if i > 0]
    T = [min(bot[r["pid"]])[0] for _, r in v if bot[r["pid"]]]; pl = [pull[r["pid"]] for _, r in v if r["pid"] in pull]
    nb = [len(bot[r["pid"]]) for _, r in v]; eb = [sum(e for _, e in bot[r["pid"]]) for _, r in v]
    print("%s..%s  launches %2d  gap min p50 %.1f  T p50 %s (min %s max %s)  bot buys/pool p50 %d  bot ETH/pool p50 %.2f  pull offset p50 %s (min %s max %s)" % (
        time.strftime("%H:%M", time.gmtime(v[0][1]["t"])), time.strftime("%H:%M", time.gmtime(v[-1][1]["t"])), len(v), S.median(gaps) / 60 if gaps else 0,
        S.median(T) if T else None, min(T) if T else None, max(T) if T else None, S.median(nb), S.median(eb), S.median(pl) if pl else None, min(pl) if pl else None, max(pl) if pl else None))
last = rows[-1]
print("last launch %s block %d tx %s sender %s token %s pool %s; pulled at +%s blocks; bot buys %d (%.2f ETH), last bot buy at +%s" % (
    time.strftime("%m-%d %H:%M:%S", time.gmtime(last["t"])), last["b"], last["h"], last["from"], last["c1"], last["pid"], pull.get(last["pid"]), len(bot[last["pid"]]), sum(e for _, e in bot[last["pid"]]), max(bot[last["pid"]])[0]))
