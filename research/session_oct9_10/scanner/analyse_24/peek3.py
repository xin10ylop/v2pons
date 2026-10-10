import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
for pid in ["0x5228362b5cea980b5c575a9427a41914958dd327e37c027ffeda241f3305bbc2", "0xdab833d4710ea7746fe5831a93e16921f427798ab13daf7eed55eb50a6a20e94", "0x91fb2b54c4864660bc0904d0235d8a3536438013b26806aec43e67d82a7ddeed"]:
    p = P[pid]; t = T[p["launch_tx"]]
    inp = t.get("input") or t["input512"]
    body = inp[10:]
    print(pid[:12], t["selector"], t["calldata_len"], t["gas"], t["gas_price"], t["max_prio"])
    for i in range(0, len(body), 64):
        w = body[i:i+64]
        try: a = bytes.fromhex(w).decode("ascii") if all(32 <= b < 127 or b == 0 for b in bytes.fromhex(w)) and any(b for b in bytes.fromhex(w)) else ""
        except Exception: a = ""
        print("  ", i // 64, w, int(w, 16) if len(w) == 64 and int(w,16) < 10**30 else "", a.strip("\x00"))
