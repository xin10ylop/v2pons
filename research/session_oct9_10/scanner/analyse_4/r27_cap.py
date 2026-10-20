#!/usr/bin/env python3
"""capacity of the 0x27fad47c fresh-wallet buys (calldata word 6 = amountIn, word 7 = minOut): the ETH ahead of the first one before
its output falls under its own minOut, and the share of the burst that survives our 0.0058 ETH ahead"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ana import *   # noqa
R27 = "0x27fad47c0abef79bfe44830f170ec0724ded5d12"
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = ["0x38d5b40da0d4f509dc3959f28a11de7d0b2e0b400766e1b85a34038e1c89b074", "0x7b132190bdfe520e67a1e9550f3f0c48991195b1d9973bca329517afbca8b87b",
        "0x7c15bf5b370fb0b3e0dd6ea061c6a3cee650892ccb83b075da2c560f70f211ad"]
E = load_events(set(pids)); out = {}
for pid in pids:
    pl = Pool(P[pid], E[pid], T, M)
    b = [x for x in pl.seq if x["to"] == R27]
    x = b[0]; mo = word(x["input"], 7); ain = word(x["input"], 6)
    s_pre, L_pre = pl.state_before(x["bn"], x["li"])
    quote = v4math.buy_out_int(int(pl.s_eff), pl.L0, x["eth"], x["fee"])
    rm = room(int(s_pre), L_pre, x["eth"], x["fee"], mo, hi=10**21)
    mf = lambda y: word(y["input"], 7) if y["to"] == R27 and y["input"] else None
    t = pl.trade(pl.b0 + 1, max(y["bn"] for y in b) + 1, minout_check=mf)
    out[pid] = {"amountIn_word6": ain, "minOut_word7": mo, "minOut_over_launch_quote": mo / quote, "room_eth": rm, "front_0.0058_with_minout_check": round(t["ret"], 4),
                "dropped": len(t["dropped"])}
    print(pid[:12], out[pid])
json.dump(out, open(os.path.join(HERE, "r27_cap.json"), "w"), indent=1)
