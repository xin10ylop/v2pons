#!/usr/bin/env python3
"""Verifier's own raw-data fetch (independent of follow.py / cache_follow.pkl).
For each 'orig' launch of Oct 8: the launch receipt, every Swap/ModifyLiquidity log of the pool from the launch to +600,
the pool's ModifyLiquidity logs to +60000 (the first removal), and every block launch..launch+160 with full transactions,
slimmed to what the feed replay needs (type, from, to, value, input if it carries the token, index, hash) + baseFeePerGas.
Writes raw/<block>.json per launch.   python3 vfetch.py [launch_block ...]"""
import sys, os, json, concurrent.futures as cf
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, T_INIT
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw")
D = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/oct8_pools.json"))
ORIG = sorted([p for p in D["pools"] if p["kind"] == "orig"], key=lambda p: p["block"])
SCAN = 161


def one(p):
    fn = os.path.join(RAW, f"{p['block']}.json")
    if os.path.exists(fn):
        return fn
    b0 = p["block"]; head = int(rpc("eth_blockNumber", []), 16)
    rec = rpc("eth_getTransactionReceipt", [p["tx"]])
    tok = None
    for l in rec["logs"]:
        if l["address"].lower() == PM and l["topics"] and l["topics"][0] == T_INIT and l["topics"][1] == p["pid"]:
            tok = l["topics"][3][-40:]
    near = logs({"address": PM, "topics": [[T_SWAP, T_ML], p["pid"]]}, b0, min(b0 + 600, head))
    ml = logs({"address": PM, "topics": [T_ML, p["pid"]]}, b0, min(b0 + 60000, head))
    blocks = batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(SCAN)])
    slim = []
    tb = tok.lower() if tok else None
    for b in blocks:
        txs = []
        for t in b["transactions"]:
            inp = t["input"].lower()
            carries = tb is not None and tb in inp
            txs.append({"i": int(t["transactionIndex"], 16), "h": t["hash"], "type": t["type"], "from": t["from"].lower(), "to": (t.get("to") or "").lower(),
                        "value": int(t["value"], 16), "sel": inp[:10], "len": (len(inp) - 2) // 2, "input": inp if carries else None})
        slim.append({"n": int(b["number"], 16), "ts": int(b["timestamp"], 16), "bf": int(b["baseFeePerGas"], 16), "txs": txs})
    json.dump({"p": p, "rec": rec, "token": tok, "near": near, "ml": ml, "blocks": slim, "head": head}, open(fn, "w"))
    return fn


if __name__ == "__main__":
    want = [int(x) for x in sys.argv[1:]]
    todo = [p for p in ORIG if not want or p["block"] in want]
    with cf.ThreadPoolExecutor(3) as ex:
        for fn in ex.map(one, todo):
            print(fn, flush=True)
