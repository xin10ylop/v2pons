"""Skeptic 1, candidate 5 ("a 1444-byte PositionManager launch, any line, 1-4 blocks before T"). Stage 1, on a slice the finder never used:
the 12 hours BEFORE the precursor angle's window (its pools start at block 85734703), i.e. blocks 85311700..85734702 (Oct 10 21:24 ->
Oct 11 ~09:45 UTC). Every Initialize on the PoolManager in the slice (any pair, any hook), its transaction -> the stream of 1,444-byte
PositionManager calls (any value, any line); the 3.0 pools (value 3.0 ETH, fee 10000, spacing 200, ETH pair, no hook, the line's price);
their Swap / ModifyLiquidity logs to L+400 and the transactions of every swap to L+90 and every liquidity call -> pools.json, stream.json.
Read-only, public RPC only."""
import sys, json, collections, os
from lib import *
START, END = int(sys.argv[1]) if len(sys.argv) > 1 else 85311700, int(sys.argv[2]) if len(sys.argv) > 2 else 85734702
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
fn = f"init_{START}_{END}.json"
if os.path.exists(fn): ini = json.load(open(fn))
else:
    ini = []
    for a in range(START, END + 1, 20000):
        ini += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 19999, END))
    json.dump(ini, open(fn, "w"))
b0 = rpc("eth_getBlockByNumber", [hex(START), False]); b1 = rpc("eth_getBlockByNumber", [hex(END), False])
t0, t1 = int(b0["timestamp"], 16), int(b1["timestamp"], 16)
print(f"slice {START}..{END}: {utc(t0)} -> {utc(t1)} UTC, {(END-START)/(t1-t0):.2f} blocks/s; Initialize logs {len(ini)}", flush=True)
txs = gettx([l["transactionHash"] for l in ini])
stream = []; pools = []; vals = collections.Counter()
for l, t in zip(ini, txs):
    if not t: continue
    clen = (len(t["input"]) - 2) // 2; to = (t.get("to") or "").lower(); v = int(t["value"], 16)
    if to == POSM and clen == 1444:
        line = {3 * 10 ** 18: "3.0", 2433328500000000000: "2.433"}.get(v, f"v{v/1e18:g}")
        vals[line] += 1
        stream.append({"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"], "from": t["from"].lower(), "value": v, "line": line,
                       "pid": l["topics"][1], "c0": "0x" + l["topics"][2][-40:], "hook": W(l["data"], 2), "sp": W(l["data"], 3), "fee": W(l["data"], 0), "ts_": sgn(W(l["data"], 1))})
        if line == "3.0" and int(l["topics"][2], 16) == 0 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30:
            pools.append({"line": "3.0", "pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                          "launch_tx": l["transactionHash"], "launcher": t["from"].lower()})
        elif line == "3.0": print("  3.0-valued 1444-byte launch of another shape", l["transactionHash"])
# 1444-byte PositionManager txs that are not Initialize-bearing are checked in s3 against whole blocks
print("1444-byte PositionManager launches with an Initialize in the slice:", len(stream), dict(vals), flush=True)
print("other Initialize senders/targets:", collections.Counter(((t.get("to") or "")[:10].lower(), (len(t["input"]) - 2) // 2) for t in txs if t and not ((t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444)).most_common(8))
pools.sort(key=lambda p: p["L"]); stream.sort(key=lambda s: (s["bn"], s["ti"]))
print("3.0 pools:", len(pools), flush=True)
ev = collections.defaultdict(list)
for i in range(0, len(pools), 20):
    g = pools[i:i + 20]; a = g[0]["L"]; b = g[-1]["L"] + 400
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b):
        ev[l["topics"][1]].append(l)
    print(f"  events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
need = [e["tx"] for p in pools for e in p["ev"] if (e["kind"] == "ml" or e["bn"] <= p["L"] + 90)]
print("swap/ml txs to fetch:", len(set(need) - set(kv_tx.d)), flush=True)
gettx(need)
json.dump({"start": START, "end": END, "t0": t0, "t1": t1, "pools": pools}, open("pools.json", "w"))
json.dump({"start": START, "end": END, "t0": t0, "t1": t1, "stream": stream}, open("stream.json", "w"))
print("done", flush=True)
