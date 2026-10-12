"""Full-block scan of the wind-down minutes: every tx to the hub 0x6c3bd8f6 (and from it); decode the bridge deposit logs."""
import kc, json, collections
HUB = "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"
b9 = json.load(open(kc.p("k09_buyers.json")))
buyers = set(b9["callers2433"])
fn = kc.p("k11_blocks_cache.jsonl"); have = {}
try:
    for l in open(fn): r = json.loads(l); have[r["b"]] = r
except FileNotFoundError: pass
A, B = 86313950, 86315000
need = [b for b in range(A, B + 1) if b not in have]
for i in range(0, len(need), 20):
    ch = need[i:i + 20]
    res = kc.R.batch("eth_getBlockByNumber", [[hex(b), True] for b in ch])
    with open(fn, "a") as f:
        for b, r in zip(ch, res):
            row = {"b": b, "t": int(r["timestamp"], 16), "txs": [[x["hash"], x["from"].lower(), (x.get("to") or "").lower(), int(x["value"], 16), x["input"][:10], int(x["nonce"], 16)] for x in r["transactions"]]}
            have[b] = row; f.write(json.dumps(row) + "\n")
ins = [(b, have[b]["t"], *x) for b in range(A, B + 1) for x in have[b]["txs"] if x[2] == HUB]
outs = [(b, have[b]["t"], *x) for b in range(A, B + 1) for x in have[b]["txs"] if x[1] == HUB]
print("blocks %d..%d (%s..%s): txs to hub %d, total %.6f ETH; from hub %d" % (A, B, kc.ts(have[A]["t"]), kc.ts(have[B]["t"]), len(ins), sum(x[5] for x in ins) / 1e18, len(outs)))
cl = collections.Counter(); val = collections.Counter()
for x in ins:
    k = "2.433 bot-buyer" if x[3] in buyers and b9["now"][x[3]][1] > 1000 else ("2.433 launch wallet (puller)" if x[3] in buyers else "other")
    cl[k] += 1; val[k] += x[5]
for k in cl: print("  %-30s %3d transfers %.6f ETH" % (k, cl[k], val[k] / 1e18))
print("  distinct 2.433 bot-buyers that swept to hub: %d of %d" % (len(set(x[3] for x in ins if x[3] in buyers and b9["now"][x[3]][1] > 1000)), sum(1 for a in buyers if b9["now"][a][1] > 1000)))
print("  first/last inflow:", kc.ts(ins[0][1]), kc.ts(ins[-1][1]))
# bridge logs
for h in ("0x8d18b0ee04940255815ec638c86e90570bb8dfd6fb3a360e677a62fa86b8ddcf", "0xc04476ce4a9676852106a1e35ad37b2be0aaa9425a28af70a5d45cebb922f5d3"):
    r = kc.R.call("eth_getTransactionReceipt", [h])
    for l in r["logs"]:
        if l["address"].lower() == "0xd29c85f15df544ba632c9e25829fd29d767d7978":
            t = l["topics"]; d = l["data"]
            words = [d[2 + 64 * i: 2 + 64 * (i + 1)] for i in range((len(d) - 2) // 64)]
            print(h[:12], "spoke log topics: destChain %d depositId %d depositor 0x%s" % (int(t[1], 16), int(t[2], 16), t[3][-40:]))
            print("    data words 0..6:", ["0x" + w.lstrip("0")[:40] for w in words[:7]])
