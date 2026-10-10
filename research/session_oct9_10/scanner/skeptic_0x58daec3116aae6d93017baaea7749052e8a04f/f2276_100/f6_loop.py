"""Skeptic f2276/100: where a funded launcher's ETH goes before its launch. Wallet 0x0440d6cf received 14.38 ETH from the collector
(the previous launcher's pulled ETH) at block 84,326,064 and launched pool 0xf7a2d60f at 84,331,074 with nonce 3. Its token's own logs
date its nonce-0/1 txs; then every block of the window is read with full transactions to find its txs (to, value, selector)."""
import sys, os, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs
from eth_utils import keccak
import rlp
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import load_pools
P = load_pools()
W_ = "0x0440d6cf883a87959708947e2aa24beff829a54a"; RECV = 84_326_064
pl = [p for p in P.values() if p["launch_from"] == W_][0]; LB = pl["launch_block"]; tok = pl["token"]
for n in range(3):
    a = "0x" + keccak(rlp.encode([bytes.fromhex(W_[2:]), n]))[-20:].hex()
    print("create(wallet, nonce %d) =" % n, a, "== token" if a == tok else "")
tl = logs({"address": tok}, RECV - 20_000, LB)
print("token logs before launch:", [(int(l["blockNumber"], 16), l["topics"][0][:10]) for l in tl][:6])
cp = os.path.join(D, "loop_blocks.json")
C = json.load(open(cp)) if os.path.exists(cp) else {}
lo = min([RECV] + [int(l["blockNumber"], 16) for l in tl]) - 200; hi = LB
need = [b for b in range(lo, hi + 1) if str(b) not in C]
print("blocks to read", len(need), flush=True)
for j in range(0, len(need), 50):
    res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in need[j:j + 50]])
    for b, blk in zip(need[j:j + 50], res):
        C[str(b)] = [[t["from"], t["to"], int(t["value"], 16), t["input"][:10], t["hash"], int(t["nonce"], 16)] for t in (blk or {}).get("transactions", [])
                     if t["from"] == W_ or (t["to"] or "") == W_]
    if j % 1000 == 0: json.dump(C, open(cp, "w")); print("  ", j, flush=True)
    time.sleep(0.15)
json.dump(C, open(cp, "w"))
for b in sorted(C, key=int):
    for t in C[b]: print("block", b, "from", t[0], "to", t[1], "value", t[2] / 1e18, "sel", t[3], "nonce", t[5], "hash", t[4])
