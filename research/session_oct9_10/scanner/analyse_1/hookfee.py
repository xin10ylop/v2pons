"""Family 1 (launcher 0xc763b179, hook 0xae4c0cf7): read the hook's fee events from receipts of a sample of swaps (one POST)."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
P = load_pools(); F = load_families()
key = "0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1796|10000|200|false"
pids = F[key]["pids"]
E = load_events(set(pids)); T = load_txs()
CACHE = "hookfee_rcpts.json"
want = []
for i, pid in enumerate(pids):
    sw = E[pid]["swaps"]
    if not sw: continue
    buys = [s for s in sw if s["a0"] < 0 and s["tx"] in T]
    sells = [s for s in sw if s["a0"] > 0 and s["tx"] in T]
    if buys and i % 4 == 0: want.append(buys[0]["tx"])
    if sells: want.append(sells[0]["tx"])
want = list(dict.fromkeys(want))[:60]
if os.path.exists(CACHE): R = json.load(open(CACHE))
else:
    R = dict(zip(want, batch([("eth_getTransactionReceipt", [h]) for h in want]))); json.dump(R, open(CACHE, "w"))
HOOK = "0xae4c0cf7c3feb79e0c244edbc6a3f8a3290940cc"
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
def s128(x): return x - (1 << 256) if x >= (1 << 255) else x
txpid = {}
for pid in pids:
    for s in E[pid]["swaps"]: txpid[s["tx"]] = (pid, s)
rows = []
for h, r in R.items():
    pid, s = txpid[h]; t = T[h]
    topics = collections.Counter(l["topics"][0][:10] for l in r["logs"] if l["address"] == HOOK)
    fee_ev = [l for l in r["logs"] if l["address"] == HOOK and l["topics"][0][:10] in ("0x8d1f1ed7", "0x5a2eb160")]
    if not fee_ev: print("nofee", h, topics); continue
    l = fee_ev[0]; a, b, c = W(l["data"], 0), W(l["data"], 1), W(l["data"], 2)
    side = "buy" if l["topics"][0][:10] == "0x8d1f1ed7" else "sell"
    if side == "buy": rate = c / (a + c)        # a = ETH into the pool, c = hook fee: fee share of the gross ETH in
    else: rate = c / b                           # b = ETH out of the pool, c = hook fee
    rows.append((P[pid]["launch_block"], pid[:10], side, s["bn"] - P[pid]["launch_block"], t["to"][:10], round(rate, 5), -s["a0"] if side == "buy" else s["a0"], a, b, c, t["value_wei"]))
rows.sort()
for x in rows: print(x)
