"""Stage 9 (live, the only part not on my old slice): is T's buyer wallet funded or touched INTERNALLY (no tx of its own, no calldata/log
mention) in the blocks before T? Historical state on the public RPC reaches back only ~6,000 blocks (~10 min), so this polls the chain for new
3.0 launches for DUR seconds and, for each pool once its bot buy is found, reads the buyer's ETH balance and nonce at every block T-15..T and at
T+1 (eth_getBalance / eth_getTransactionCount, read-only). A balance change between blocks with no tx of the buyer's own = an internal transfer.
-> s9_live_balance.jsonl (one line per pool), s9_live_balance.out"""
import sys, json, time
from lib import *
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 3000
t_end = time.time() + DUR
start = int(rpc("eth_blockNumber", []), 16) - 3000
seen = set(); pending = {}; out = open("s9_live_balance.jsonl", "a")
print("start block", start, flush=True)
while time.time() < t_end:
    head = int(rpc("eth_blockNumber", []), 16)
    for l in logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, start, head):
        if not (W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30): continue
        pid = l["topics"][1]
        if pid in seen: continue
        seen.add(pid)
        t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
        if (t.get("to") or "").lower() != POSM or (len(t["input"]) - 2) // 2 != 1444 or int(t["value"], 16) != 3 * 10 ** 18: continue
        pending[pid] = {"pid": pid, "L": int(l["blockNumber"], 16), "token": "0x" + l["topics"][3][-40:]}
    start = head - 50
    for pid, p in list(pending.items()):
        if head < p["L"] + 70: continue
        sw = logs({"address": PM, "topics": [T_SWAP, pid]}, p["L"], p["L"] + 70)
        T = None
        for s in sorted(sw, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16))):
            if sgn(W(s["data"], 0)) >= 0: continue
            tx = rpc("eth_getTransactionByHash", [s["transactionHash"]])
            if (tx.get("to") or "").lower() == BOT and tx["input"][2:10] == "c1120e3d":
                T = int(s["blockNumber"], 16); buyer = tx["from"].lower(); nonce = int(tx["nonce"], 16); q = abs(sgn(W(s["data"], 0))) / 1e18; break
        del pending[pid]
        if T is None:
            out.write(json.dumps(dict(p, T=None)) + "\n"); out.flush(); print("pool", pid[:12], "no bot buy to L+70", flush=True); continue
        blks = list(range(T - 15, T + 2))
        try:
            bal = batch([("eth_getBalance", [buyer, hex(b)]) for b in blks], 20)
            non = batch([("eth_getTransactionCount", [buyer, hex(b)]) for b in blks], 20)
        except Exception as e:
            print("state read failed", str(e)[:80], flush=True); continue
        bal = [int(x, 16) if x else None for x in bal]; non = [int(x, 16) if x else None for x in non]
        ch = [(b - T, bal[i] - bal[i - 1], non[i] - non[i - 1]) for i, b in enumerate(blks) if i > 0 and bal[i] is not None and bal[i - 1] is not None and (bal[i] != bal[i - 1] or non[i] != non[i - 1])]
        rec = dict(p, T=T - p["L"], Tbn=T, buyer=buyer, nonce=nonce, q=q, bal=bal, non=non, changes=ch)
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"pool {pid[:12]} L {p['L']} T +{T - p['L']} buyer {buyer[:10]} nonce {nonce} q {q:.4f}; balance/nonce changes (d from T, dbal wei, dnonce): {ch}", flush=True)
    time.sleep(45)
print("done", flush=True)
