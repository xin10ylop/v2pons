"""d03: read every transaction that moved one of the launcher's tokens (buys, sells, transfers; the launch txs excluded), so each buy has
its sender, target, selector, gas price, nonce, value and the router call's recipient. Batched eth_getTransactionByHash on keyless archive
endpoints. -> cache/d03_txs_cache.jsonl {hash: [from, to, sel, gasPrice, nonce, value, input_len, words 0..7 of the input]}"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rpc
D = os.path.dirname(os.path.abspath(__file__)); C = os.path.join(D, "cache")
L = json.load(open(os.path.join(D, "d01_launches.json")))["launches"]; launch_tx = set(o["tx"] for o in L)
hs = set()
for ln in open(os.path.join(C, "d02_transfers_cache.jsonl")):
    r = json.loads(ln)
    if r[3] not in launch_tx: hs.add(r[3])
fn = os.path.join(C, "d03_txs_cache.jsonl"); have = set()
if os.path.exists(fn):
    for ln in open(fn): have.update(json.loads(ln).keys())
todo = sorted(hs - have); print("txs", len(hs), "to fetch", len(todo), flush=True)
f = open(fn, "a")
for i in range(0, len(todo), 500):
    part = todo[i:i + 500]
    res = rpc.batch([("eth_getTransactionByHash", [h]) for h in part], size=50)
    for h, r in zip(part, res):
        t = (r or {}).get("result")
        if not t: continue
        inp = t["input"][2:]
        f.write(json.dumps({h: [t["from"].lower(), (t.get("to") or "").lower(), inp[:8], int(t["gasPrice"], 16), int(t["nonce"], 16), int(t["value"], 16),
                                len(inp) // 2, [inp[8 + 64 * k: 8 + 64 * (k + 1)] for k in range(min(9, (len(inp) - 8) // 64))], int(t.get("type", "0x0"), 16)]}) + "\n")
    f.flush(); print("fetched", i + len(part), rpc.STATS, flush=True)
