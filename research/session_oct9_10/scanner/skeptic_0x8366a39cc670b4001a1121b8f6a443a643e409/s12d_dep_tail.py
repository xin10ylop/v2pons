"""The deployer's transactions around its sweep (nonce 8) - what is nonce 9? Blocks sweep-300..sweep+600 scanned."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import batch
D = os.path.join(HERE, "fresh"); cache = os.path.join(D, "blocks.json"); BK = json.load(open(cache))
def get(a, b):
    need = [x for x in range(a, b + 1) if str(x) not in BK]
    for i in range(0, len(need), 50):
        r = batch([("eth_getBlockByNumber", [hex(x), True]) for x in need[i:i + 50]])
        for x, blk in zip(need[i:i + 50], r):
            BK[str(x)] = [{"h": t["hash"], "from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "sel": t["input"][2:10], "nonce": int(t["nonce"], 16)} for t in blk["transactions"]]
    json.dump(BK, open(cache, "w"))
dep = "0x6ec9cfc58a26c9c6f125926759c5c12a7d342cc1"; s = 85210681
get(s - 300, s + 600)
hits = [(x, t) for x in range(s - 300, s + 601) for t in BK[str(x)] if t["from"] == dep or t["to"] == dep]
for x, t in hits: print(x - s, t["from"][:10], "->", t["to"], round(t["value"] / 1e18, 6), t["sel"], t["nonce"])
# crowd router 0x628bd69e inbound value txs in the same window
print("txs to the crowd router with value:", [(x - s, t["from"], round(t["value"] / 1e18, 4)) for x in range(s - 300, s + 601) for t in BK[str(x)] if t["to"] == "0x628bd69ecbc135cdda02ffd6d6db918f5cd835ce" and t["value"] > 0])
