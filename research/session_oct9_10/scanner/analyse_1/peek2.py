import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families()
key = "0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1796|10000|200|false"
pids = F[key]["pids"]
E = load_events(set(pids)); T = load_txs()
pid = "0xa1c471da4e24489f42004c7b0a4a22d06357dfadb1a76b8c52542f2fec0138a6"
for s in E[pid]["swaps"][:9]:
    t = T.get(s["tx"])
    if t: print(s["bn"]-P[pid]["launch_block"], s["a0"], t["value_wei"], t["hash"], t["input"][:10+64*12] if t.get("input") else t["input512"][:900])
lt = T[P[pid]["launch_tx"]]
print("LAUNCH", lt["hash"], lt["from"], lt["to"], lt["value_wei"], lt["calldata_len"]); print(lt.get("input") or lt["input512"])
