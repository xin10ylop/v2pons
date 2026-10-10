"""Decode the R75 (0x75379d5d, UR-style execute 3593564c) first buys of the 1.5-ETH operator: commands, the V4_SWAP actions and the
SWAP_EXACT_IN params (currencyIn, path, amountIn, amountOutMinimum), and the second command's words."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common13 import *  # noqa
P = load_pools(); F = load_families(); T = load_txs()
keys = [k for k in F if k.startswith("0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3236|") or k.startswith("0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3204|")]
pids = [p for k in keys for p in F[k]["pids"]]
E = load_events(set(pids))
out = []
for pid in pids:
    b0 = P[pid]["launch_block"]
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        if not (t and t["to"] == R75 and s["a0"] < 0): continue
        d = bytes.fromhex(t["input"][10:]); w = lambda o: int.from_bytes(d[o:o + 32], "big")
        cmd_off = w(0); inp_off = w(32); deadline = w(64)
        ncmd = w(cmd_off); cmds = d[cmd_off + 32: cmd_off + 32 + ncmd].hex()
        ninp = w(inp_off); base = inp_off + 32
        inputs = []
        for i in range(ninp):
            o = base + w(base + 32 * i); ln = w(o); inputs.append(d[o + 32: o + 32 + ln])
        # input 0: V4_SWAP = abi.encode(bytes actions, bytes[] params)
        x = inputs[0]; xw = lambda o: int.from_bytes(x[o:o + 32], "big")
        a_off = xw(0); p_off = xw(32); na = xw(a_off); actions = x[a_off + 32: a_off + 32 + na].hex()
        npar = xw(p_off); pb = p_off + 32
        p0 = pb + xw(pb); p0len = xw(p0); par0 = x[p0 + 32: p0 + 32 + p0len]
        pw = lambda o: int.from_bytes(par0[o:o + 32], "big")
        t0 = pw(0)  # offset of the ExactInputParams tuple
        currency_in, path_off, slip_off, amount_in, amount_out_min = pw(t0), pw(t0 + 32), pw(t0 + 64), pw(t0 + 96), pw(t0 + 128)
        second = [int.from_bytes(inputs[1][i:i + 32], "big") for i in range(0, len(inputs[1]), 32)] if ninp > 1 else None
        row = {"pid": pid, "rel": s["bn"] - b0, "from": t["from"], "nonce": t["nonce"], "commands": cmds, "actions": actions, "currency_in": hex(currency_in),
               "amount_in_eth": amount_in / 1e18, "amountOutMinimum": amount_out_min, "a0_eth": -s["a0"] / 1e18, "tokens_out": s["a1"],
               "second_cmd_words": [hex(v) if v > 10**6 else v for v in (second or [])], "deadline_minus_ts": None}
        out.append(row)
        print(pid[:10], row["rel"], cmds, actions, "in", row["amount_in_eth"], "a0", row["a0_eth"], "minOut", amount_out_min, "second", row["second_cmd_words"])
        break
json.dump(out, open(os.path.join(HERE, "decode.json"), "w"), indent=1)
