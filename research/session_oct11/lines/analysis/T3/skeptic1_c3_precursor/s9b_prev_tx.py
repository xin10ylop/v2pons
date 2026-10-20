"""Stage 9b (live): when did T's buyer send its PREVIOUS transaction? For each pool recorded by s9 (within the public RPC's ~6,000-block
state window), binary-search eth_getTransactionCount(buyer, block) over [T-4,000, T-1] for the block where its nonce reached the T tx's
nonce: that block holds the buyer's previous tx. If that lag were stable it would anchor T. -> s9b_prev_tx.jsonl / .out"""
import json, time, sys
from lib import *
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 3000
t_end = time.time() + DUR; done = set(); out = open("s9b_prev_tx.jsonl", "a")
while time.time() < t_end:
    try: recs = [json.loads(l) for l in open("s9_live_balance.jsonl")]
    except FileNotFoundError: recs = []
    for r in recs:
        if r.get("T") is None or r["pid"] in done: continue
        done.add(r["pid"]); T = r["Tbn"]; n = r["nonce"]; buyer = r["buyer"]
        def nonce_at(b): return int(rpc("eth_getTransactionCount", [buyer, hex(b)]), 16)
        try:
            lo = T - 4000
            if nonce_at(lo) >= n: res = dict(pid=r["pid"], T=r["T"], buyer=buyer, prev_lag=">4000")
            else:
                hi = T - 1
                while hi - lo > 1:
                    m = (lo + hi) // 2
                    if nonce_at(m) >= n: hi = m
                    else: lo = m
                b = rpc("eth_getBlockByNumber", [hex(hi), True]); tx = [t for t in b["transactions"] if t["from"].lower() == buyer]
                res = dict(pid=r["pid"], T=r["T"], buyer=buyer, prev_block=hi, prev_lag=T - hi, prev_to=tx[0]["to"] if tx else None, prev_sel=tx[0]["input"][:10] if tx else None)
        except Exception as e:
            res = dict(pid=r["pid"], err=str(e)[:80])
        out.write(json.dumps(res) + "\n"); out.flush(); print(res, flush=True)
    time.sleep(20)
print("done", flush=True)
