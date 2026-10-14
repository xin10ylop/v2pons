"""BNB: every token minted to the router copy 0x07cb6161 from Oct 13 16:00 UTC (block 127430000) to the head; for each, the deploy tx
(sender, nonce, value, gas limit, selector) and its venue (Uniswap v4 Initialize in our cache, or PancakeSwap V2 PairCreated)."""
import sys, json, os, collections, time; sys.path.insert(0, '.'); import rpcx
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
T_PAIR = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
RC = "0x07cb61618b69234d954022ff738a015548715533"; FAC = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"
h, th = rpcx.head("bsc_h"); A = 127430000
OUT = "c19_mints_cache.jsonl"
if not os.path.exists(OUT):
    rows = []
    for s in range(A, h + 1, 5000):
        for l in rpcx.logs("bsc_h", {"topics": [T, pad("0x" + "0" * 40), pad(RC)]}, s, min(s + 4999, h)):
            rows.append({"b": int(l["blockNumber"], 16), "tok": l["address"].lower(), "tx": l["transactionHash"]})
        print("mints scan", s, len(rows), flush=True)
    txs = rpcx.batch("bsc_h", "eth_getTransactionByHash", [[r["tx"]] for r in rows], n=10)
    for r, t in zip(rows, txs):
        r.update({"from": t["from"].lower(), "nonce": int(t["nonce"], 16), "v": int(t["value"], 16) / 1e18, "gas": int(t["gas"], 16), "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2})
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
rows = [json.loads(l) for l in open(OUT)]
inits = {}
for l in open("c11_bsc_inits_cache.jsonl"):
    r = json.loads(l); inits[r["c1"]] = r; inits[r["c0"]] = r
# PancakeSwap V2 PairCreated for these tokens (token0 or token1 topic)
toks = [r["tok"] for r in rows]; pairs = {}
for i in range(0, len(toks), 40):
    ch = [pad(t) for t in toks[i:i + 40]]
    a = min(r["b"] for r in rows[i:i + 40]); b = max(r["b"] for r in rows[i:i + 40]) + 200
    for s in range(a, b + 1, 5000):
        for flt in ({"address": FAC, "topics": [T_PAIR, ch]}, {"address": FAC, "topics": [T_PAIR, None, ch]}):
            for l in rpcx.logs("bsc_h", flt, s, min(s + 4999, b)):
                t0, t1 = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]
                pairs[t0 if t0 in toks else t1] = {"pair": "0x" + l["data"][26:66], "b": int(l["blockNumber"], 16)}
tt = lambda b: time.strftime("%m-%d %H:%M", time.gmtime(th - (h - b) * 0.45))
C = collections.Counter()
for r in rows:
    ven = "v4 %d/%d" % (inits[r["tok"]]["fee"], inits[r["tok"]]["ts_"]) if r["tok"] in inits else ("pcsv2" if r["tok"] in pairs else "none")
    r["venue"] = ven; C[(tt(r["b"])[:8], ven, round(r["v"], 4), r["gas"])] += 1
for k, v in sorted(C.items()): print(k, v)
json.dump(rows, open("c19_mints.json", "w"), indent=1)
print(rpcx.STATS)
