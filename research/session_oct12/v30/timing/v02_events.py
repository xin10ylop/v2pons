"""Per 3.0 pool: ModifyLiquidity (mint, pulls) and every Swap from L to the pull (or the head); all token Transfers into the bot router.
Refreshes the head (v02_meta.json) so late pools get their T and pulls."""
import vc, json, os, collections
R = vc.R
pools = json.load(open(vc.p("v01_launches.json"))); meta = json.load(open(vc.p("v01_meta.json")))
mf = vc.p("v02_meta.json")
if os.path.exists(mf): head = json.load(open(mf))["head"]
else:
    head = int(R.call("eth_blockNumber", []), 16); json.dump({"head": head}, open(mf, "w"))
A = meta["start"]
# 1) ModifyLiquidity for all pids, grouped
ml = []
for i in range(0, len(pools), 60):
    ids = [r["id"] for r in pools[i:i + 60]]
    a = min(r["block"] for r in pools[i:i + 60])
    ml += vc.cached_logs("v02_ml_%03d_cache.jsonl" % i, {"address": vc.PM, "topics": [vc.T_ML, ids]}, a, head, step=50000)
mlp = collections.defaultdict(list)
for l in ml:
    mlp[l["topics"][1]].append({"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "sender": vc.topaddr(l["topics"][2]),
                                "dl": vc.sgn(vc.W(l["data"], 2))})
print("ML logs", len(ml), "pools with ML", len(mlp))
# 2) Swaps per pool L..(first pull + 3) or head
fn = vc.p("v02_swaps_cache.jsonl"); done = {}
if os.path.exists(fn):
    for l in open(fn):
        r = json.loads(l); done[r["id"]] = r
for k, r in enumerate(pools):
    pulls = sorted(x["b"] for x in mlp[r["id"]] if x["dl"] < 0)
    to = min(head, pulls[0] + 3) if pulls else head
    if r["id"] in done and done[r["id"]]["to"] >= to: continue
    lg = R.logs({"address": vc.PM, "topics": [vc.T_SWAP, r["id"]]}, r["block"], to)
    row = {"id": r["id"], "a": r["block"], "to": to, "logs": [{"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "sender": vc.topaddr(l["topics"][2]),
                                                               "a0": vc.sgn(vc.W(l["data"], 0)), "a1": vc.sgn(vc.W(l["data"], 1))} for l in lg]}
    with open(fn, "a") as f: f.write(json.dumps(row) + "\n")
    done[r["id"]] = row
    if k % 50 == 0: print("swaps", k, len(pools), flush=True)
# 3) Transfers into the bot router
tr = vc.cached_logs("v02_botin_cache.jsonl", {"topics": [vc.T_TR, None, "0x" + "0" * 24 + vc.BOT[2:]]}, A - 3000, head, step=20000)
print("transfers into BOT", len(tr), "head", head)
json.dump({"ml": mlp}, open(vc.p("v02_ml.json"), "w"))
