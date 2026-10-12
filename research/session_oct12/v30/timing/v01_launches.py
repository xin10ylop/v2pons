"""Every PoolManager Initialize in the last 12 h to the head; keep the 3.0 line (currency0 ETH, fee 10000, ts 200, the 3.0 sqrtP),
then check each launch tx: to the PositionManager, value exactly 3 ETH, 1,444 B multicall. Freezes the head in v01_meta.json."""
import vc, json, os, time
R = vc.R
mf = vc.p("v01_meta.json")
if os.path.exists(mf): meta = json.load(open(mf))
else:
    head = int(R.call("eth_blockNumber", []), 16); th = int(R.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    lo, hi = head - 600000, head
    while lo < hi:  # first block with ts >= th - 12 h
        mid = (lo + hi) // 2
        if int(R.call("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < th - 12 * 3600: lo = mid + 1
        else: hi = mid
    meta = {"head": head, "t_head": th, "start": lo, "t_start": th - 12 * 3600}
    json.dump(meta, open(mf, "w"))
print("meta", meta, vc.ts(meta["t_start"]), "->", vc.ts(meta["t_head"]))
lg = vc.cached_logs("v01_inits_cache.jsonl", {"address": vc.PM, "topics": [vc.T_INIT]}, meta["start"], meta["head"], step=25000)
c = []
for l in lg:
    d = l["data"]; t = l["topics"]
    if vc.topaddr(t[2]) != vc.Z: continue
    r = {"block": int(l["blockNumber"], 16), "tx": l["transactionHash"], "id": t[1], "tok": vc.topaddr(t[3]), "fee": vc.W(d, 0), "tsp": vc.sgn(vc.W(d, 1)),
         "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtp": vc.W(d, 3)}
    if r["sqrtp"] in (vc.SQ30, vc.SQ50) or r["fee"] == 10000: c.append(r)
print("ETH-pair inits", sum(1 for l in lg if vc.topaddr(l["topics"][2]) == vc.Z), "of", len(lg), "; candidates (3.0/5.0 sqrtP or fee 10000)", len(c))
tx = vc.txs("v01_tx_cache.jsonl", [r["tx"] for r in c])
bt = vc.block_ts_map("v01_bt_cache.jsonl", [r["block"] for r in c])
out = []; rej = {}
for r in c:
    x = tx[r["tx"]]
    r.update(t=bt[r["block"]], frm=x["from"], to=x["to"], value=x["value"], clen=x["clen"], sel=x["input"][:10], nonce=x["nonce"], gas=x["gas"], idx=x["idx"])
    ok30 = (r["sqrtp"] == vc.SQ30 and r["fee"] == 10000 and r["tsp"] == 200 and r["hooks"] == vc.Z and r["to"] == vc.POSM and r["value"] == 3 * 10 ** 18 and r["clen"] == 1444 and r["sel"] == "0xac9650d8")
    if ok30: out.append(r)
    else:
        k = ("sq30" if r["sqrtp"] == vc.SQ30 else "sq50" if r["sqrtp"] == vc.SQ50 else "other", r["fee"], r["tsp"], r["value"] / 1e18, r["clen"], r["to"][:10])
        rej[k] = rej.get(k, 0) + 1
out.sort(key=lambda r: r["block"])
json.dump(out, open(vc.p("v01_launches.json"), "w"))
print("3.0 launches", len(out), "first", vc.ts(out[0]["t"]), "last", vc.ts(out[-1]["t"]))
print("rejected candidate shapes:", sorted(rej.items(), key=lambda kv: -kv[1])[:12])
import collections
hc = collections.Counter(vc.hh(r["t"]) for r in out)
print("per hour:", sorted(hc.items()))
nc = collections.Counter("lo" if r["nonce"] < 50 else "hi" for r in out); print("launcher nonce class:", nc)
