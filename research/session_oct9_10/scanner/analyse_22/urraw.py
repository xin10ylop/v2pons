import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
from eth_abi import decode
T = load_txs(); T.update(json.load(open("extra_txs.json")))
h = [k for k, t in T.items() if t["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904" and t["calldata_len"] == 1284 and t["nonce"] == 0 and t.get("input")][0]
t = T[h]; b = bytes.fromhex(t["input"][10:])
cmds, inputs, dl = decode(["bytes", "bytes[]", "uint256"], b)
print("cmds", cmds.hex(), "value", t["value_wei"])
actions, params = decode(["bytes", "bytes[]"], inputs[0])
print("actions", actions.hex())
for j, p in enumerate(params):
    print("param", j, len(p))
    for i in range(0, len(p), 32): print("   %3d %s %d" % (i // 32, p[i:i+32].hex(), int.from_bytes(p[i:i+32], "big") if i // 32 < 40 else 0))
print("sweep input", inputs[1].hex() if len(inputs) > 1 else None)
