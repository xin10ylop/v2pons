"""decode the Universal Router execute() calldata of the 2-ETH operator's crowd buys (1,284 bytes) and of family 3's 0x75379d5d buys:
commands, and for V4_SWAP (0x10) the actions and the ExactInputSingle params (amountIn, amountOutMinimum). Informative only."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
from eth_abi import decode
T = load_txs(); T.update(json.load(open("extra_txs.json")))
def dec(inp):
    b = bytes.fromhex(inp[10:])
    try: cmds, inputs, dl = decode(["bytes", "bytes[]", "uint256"], b)
    except Exception:
        cmds, inputs = decode(["bytes", "bytes[]"], b); dl = None
    out = {"cmds": cmds.hex(), "deadline": dl, "parts": []}
    for c, i in zip(cmds, inputs):
        c &= 0x3f
        if c == 0x10:
            actions, params = decode(["bytes", "bytes[]"], i)
            part = {"cmd": "V4_SWAP", "actions": actions.hex()}
            for a, p in zip(actions, params):
                if a == 0x06:
                    (key, zf1, amt_in, min_out, hook) = decode(["(address,address,uint24,int24,address)", "bool", "uint128", "uint128", "bytes"], p)[0] if False else decode(["((address,address,uint24,int24,address),bool,uint128,uint128,bytes)"], p)[0]
                    part.update({"fee": key[2], "zeroForOne": zf1, "amountIn": amt_in, "amountOutMinimum": min_out})
            out["parts"].append(part)
        else:
            out["parts"].append({"cmd": hex(c), "len": len(i)})
    return out
import collections
seen = collections.Counter()
for h, t in T.items():
    inp = t.get("input")
    if not inp or t.get("selector") != "3593564c": continue
    key = (t["to"], t["calldata_len"])
    if key not in (("0x8876789976decbfcbbbe364623c63652db8c0904", 1284), ("0x75379d5d2ea4c98aeaa57f32e233707550ab03f0", 1540)): continue
    if seen[key] >= 4: continue
    seen[key] += 1
    try: print(key[0][:10], key[1], t["nonce"], t["value_wei"] / 1e18, dec(inp))
    except Exception as e: print(key, "decode error", e, inp[:300])
