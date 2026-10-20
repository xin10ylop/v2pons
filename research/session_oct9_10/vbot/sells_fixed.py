#!/usr/bin/env python3
"""Every Universal Router call (24856bc3, 1,060 bytes) carrying a family token in the cached blocks: the fixed byte offsets of the bot's
sell layout vs the generic ur_swaps decode; and the bot-router buys (c1120e3d, 324 bytes) and pulls (a0f7978d, 260 bytes) on family tokens.
    python3 sells_fixed.py"""
import os, sys, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
import fetch_blocks as fb
from vbot_feed import ur_swaps, bot_buy, bot_pull, launch_of, UNIVERSAL_ROUTER, BOT_ROUTER
from launch_decode import _u
R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
TOK = {bytes.fromhex(r["token"][2:].lower()) for r in R if fam(r)}
PC = pickle.load(open(os.path.join(HERE, "cache_post_launch.pkl"), "rb"))
for l in PC["inits"]: TOK.add(bytes.fromhex(l["topics"][3][-40:]))
HEAD = bytes.fromhex("24856bc3" + "%064x" % 0x40 + "%064x" % 0x80 + "%064x" % 1 + "10" + "00" * 31 + "%064x" % 1 + "%064x" % 0x20)
c = collections.Counter()
for f in sorted(os.listdir(fb.BD)):
    if not f.endswith(".pkl"): continue
    for n, (ts, bf, txs) in fb.load_chunk(int(f[:-4])).items():
        for t in txs:
            to = t[3][2:]; d = t[9]; v = t[4]
            if to == UNIVERSAL_ROUTER and d[:4].hex() == "24856bc3" and len(d) == 1060 and d[592:612] in TOK:
                c["ur 1060 sells on family tokens"] += 1
                g = ur_swaps(to, v, d)
                fixed = {"token": d[592:612].hex(), "zf1": _u(d, 708) != 0, "amount_in": _u(d, 740), "min_out": _u(d, 772)}
                ok = len(g) == 1 and g[0]["key"]["currency1"] == fixed["token"] and g[0]["zero_for_one"] == fixed["zf1"] and g[0]["amount_in"] == fixed["amount_in"] and d[:len(HEAD)] == HEAD \
                     and d[324:327] == bytes([6, 12, 15]) and g[0]["key"]["fee"] == 10000 and g[0]["key"]["tick_spacing"] == 200
                c["  fixed offsets == generic decode (head, actions 060c0f, key)"] += ok; c["  zeroForOne false"] += not fixed["zf1"]; c[f"  value {'0' if v == 0 else '>0'}"] += 1
            elif to == BOT_ROUTER:
                b = bot_buy(to, v, d); p = bot_pull(to, v, d)
                if b and bytes.fromhex(b["token"]) in TOK: c["bot-router buys on family tokens"] += 1; c["  buy value > 0 and token at [80:100]"] += (v > 0 and d[80:100] == bytes.fromhex(b["token"]))
                elif p and bytes.fromhex(p["token"]) in TOK: c["bot-router pulls on family tokens"] += 1
                else: c[f"bot-router other {d[:4].hex()} len {len(d)} value>0 {v > 0}"] += 1
for k, v in c.items(): print(f"{k}: {v}")
