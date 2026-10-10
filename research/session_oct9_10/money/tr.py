"""block-scan tracer: every plain transaction to/from a set of addresses in a block window (no archive, no trace API)"""
import sys, json, os, pickle
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocks.pkl")
try: BL = pickle.load(open(CACHE, "rb"))
except Exception: BL = {}
def blocks(a, b):
    need = [n for n in range(a, b + 1) if n not in BL]
    for i in range(0, len(need), 100):
        ch = need[i:i + 100]
        for n, blk in zip(ch, batch([("eth_getBlockByNumber", [hex(n), True]) for n in ch])):
            if blk: BL[n] = [(x["hash"], x["from"].lower(), (x.get("to") or "").lower(), int(x["value"], 16), int(x["nonce"], 16), x["input"][:10]) for x in blk["transactions"]]
    return [(n, t) for n in range(a, b + 1) for t in BL.get(n, [])]
def save(): pickle.dump(BL, open(CACHE, "wb"))
def touching(addrs, a, b):
    s = {x.lower() for x in addrs}
    return [(n, t) for n, t in blocks(a, b) if t[1] in s or t[2] in s]
def show(n, t, ref=None):
    h, f, to, v, nonce, sel = t
    return f"blk {n}{'' if ref is None else f' ({n-ref:+d})'} {f[:12]} -> {to[:12]} {v/1e18:.4f} ETH nonce {nonce} {sel}"
