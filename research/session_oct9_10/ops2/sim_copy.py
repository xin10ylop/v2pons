"""Same permission test on one-shot copy 0xd1cc99aa33.. (code hash 2793923d): new salt, random sender + random recipient, 1000 ETH override."""
import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
from chain import post, rpc
from eth_abi import encode, decode
from decode import dec, TYPES, NAMES
CP = "0xd1cc99aa33b6cfc5246d8f7c4fc4492c367425bc"
t = rpc("eth_getTransactionByHash", ["0x081bd2300a44d8864460148abf5541d42053205df24974e1e2cf1d1318b9fd0c"])  # a real copy launch (via copy 0x8ea696db)
d = dec(t["input"]); RND = "0x" + os.urandom(20).hex(); R2 = "0x" + os.urandom(20).hex()
v = dict(d); v.update(salt=os.urandom(32).hex(), recipient=R2)
data = "0x2fcb9108" + encode(TYPES, [bytes.fromhex(v["salt"])] + [v[n] for n in NAMES[1:]]).hex()
r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"from": RND, "to": CP, "data": data, "value": t["value"], "gas": hex(5_000_000)}, "latest", {RND: {"balance": hex(10**21)}}]})
print("copy", CP, "random sender", RND, "recipient", R2, "value", int(t["value"], 16) / 1e18, "->", ("SUCCESS token 0x" + r["result"][26:66] + " NFT id %d" % int(r["result"][-64:], 16)) if "result" in r else r["error"])
