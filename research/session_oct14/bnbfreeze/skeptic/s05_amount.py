"""Does the amount matter? transfer(dead, amt) from our wallet at head (pn) and archive (se) around the mark. Read-only."""
import sys, json
sys.path.insert(0, __import__("os").path.dirname(__file__))
from rpc import raw
TOK = "0x950e681819a68f595bb3db313346393d64f66bb5"; US = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"; DEAD = "0x000000000000000000000000000000000000dead"
def transfer(to, amt): return "0xa9059cbb" + "00" * 12 + to[2:] + "%064x" % amt
def call(amt, blk, ep):
    r = raw("eth_call", [{"from": US, "to": TOK, "data": transfer(DEAD, amt), "gas": hex(300000)}, blk], ep)
    return ("ok:" + r["result"][-4:]) if "result" in r else "REV" if "revert" in str(r["error"]).lower() else "E:" + str(r["error"])[:50]
amts = (1, 2, 100, 10**4, 10**6, 10**8, 10**10, 268154926265, 26815492626516)
print("head pn:", [(a, call(a, "latest", "pn")) for a in amts])
for ep in ("se", "bm"):
    for b in (127550559, 127550560, 127550600, 127555000):
        print(ep, b, [(a, call(a, hex(b), ep)) for a in (1, 10**6, 10**8, 268154926265)])
