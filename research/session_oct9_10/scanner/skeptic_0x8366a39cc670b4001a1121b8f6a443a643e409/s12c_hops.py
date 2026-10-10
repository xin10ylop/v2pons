"""Back-trace the funding hops of two deployers (blocks scanned for a transaction TO the wallet, up to 3,000 blocks back per hop)."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import rpc, batch
D = os.path.join(HERE, "fresh"); cache = os.path.join(D, "blocks.json"); BK = json.load(open(cache)) if os.path.exists(cache) else {}
def get(a, b):
    need = [x for x in range(a, b + 1) if str(x) not in BK]
    for i in range(0, len(need), 50):
        r = batch([("eth_getBlockByNumber", [hex(x), True]) for x in need[i:i + 50]])
        for x, blk in zip(need[i:i + 50], r):
            BK[str(x)] = [{"h": t["hash"], "from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "sel": t["input"][2:10], "nonce": int(t["nonce"], 16)} for t in blk["transactions"]]
    json.dump(BK, open(cache, "w"))
def find_to(addr, before, span=3000, step=300):
    b = before
    while b > before - span:
        a = b - step; get(a, b)
        hits = [(x, t) for x in range(b, a - 1, -1) for t in BK[str(x)] if t["to"] == addr]
        if hits: return hits
        b = a - 1
    return []
money = json.load(open(os.path.join(HERE, "money.json")))
out = []
for f in money["funding"][:2]:
    cur = f["funding"][0][1]; blk = f["token_mint_block"] + f["funding"][0][0]
    chain = [(f["dep"], blk)]
    for hop in range(3):
        hits = find_to(cur, blk - 1)
        if not hits: chain.append((cur, "no inbound tx found in 3000 blocks")); break
        x, t = hits[0]
        chain.append((cur, x, t["from"], round(t["value"] / 1e18, 5), t["sel"], t["nonce"]))
        print(" hop", hop, cur[:10], "funded at", x, "by", t["from"], round(t["value"] / 1e18, 5), "ETH sel", t["sel"] or "-", "sender nonce", t["nonce"], flush=True)
        cur, blk = t["from"], x
    out.append(chain)
json.dump(out, open(os.path.join(HERE, "hops.json"), "w"), indent=1)
