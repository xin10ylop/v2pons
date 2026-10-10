#!/usr/bin/env python3
"""Out-of-sample: every PM1444-like launch after the census head (84,238,619) up to now. Fetch the launch txs (input) and their Initialize logs,
test the strict fingerprint and the decoder (pool id, key, sqrtP vs the Initialize log). Cache vbot/cache_post_launch.pkl.
    python3 post_check.py"""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, SCR); sys.path.insert(0, HERE)
from chain import rpc, batch, logs, PM, T_INIT
from launch_decode import decode_launch
from vbot_feed import launch_of, POSITION_MANAGER
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
sg = lambda x: x - (1 << 256) if x >> 255 else x
CP = os.path.join(HERE, "cache_post_launch.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {"to": 84238619, "inits": [], "tx": {}}
head = int(rpc("eth_blockNumber", []), 16) - 5
a = C["to"] + 1
while a <= head:
    b = min(a + 49999, head); C["inits"] += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); C["to"] = b; a = b + 1
need = sorted({l["transactionHash"] for l in C["inits"]} - set(C["tx"]))
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: C["tx"][h] = t
pickle.dump(C, open(CP, "wb"))
print("post-census pools (ETH pairs):", len(C["inits"]), "to block", C["to"])
st = collections.Counter(); blocks = []
for l in C["inits"]:
    t = C["tx"].get(l["transactionHash"])
    if t is None: continue
    to = (t["to"] or "")[2:].lower(); val = int(t["value"], 16); data = bytes.fromhex(t["input"][2:]); d = l["data"]
    loose = to == POSITION_MANAGER and data[:4].hex() == "ac9650d8" and len(data) == 1444 and val == 3 * 10**18 and W(d, 0) == 10000 and sg(W(d, 1)) == 200
    p = launch_of(to, val, data, strict=True); p5 = launch_of(to, val, data, strict=False)
    if loose: st["census-style family (PM, 1444 bytes, 3 ETH, fee 1%, ts 200)"] += 1
    if p5: st["L5 (key/layout + 3 ETH)"] += 1
    if p:
        st["L6 strict"] += 1; blocks.append(int(l["blockNumber"], 16))
        ok = p["pid"] == l["topics"][1] and p["token"] == l["topics"][3][-40:] and p["sqrt_p"] == W(d, 3)
        st["strict: pid/token/sqrtP == Initialize"] += ok
    if loose and not p: st["census-style but NOT strict"] += 1
    if p and not loose: st["strict but not census-style"] += 1
    g = decode_launch(data)
    if g and g["pid"] == l["topics"][1]: st["generic decoder pid ok (any launch)"] += 1
for k, v in st.items(): print(f"  {k}: {v}")
print("strict launches: first", min(blocks) if blocks else None, "last", max(blocks) if blocks else None, "head", head)
json.dump({"stats": st, "blocks": blocks, "head": head}, open(os.path.join(HERE, "post_check.json"), "w"))
