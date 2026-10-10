"""For every one-shot launcher copy (other_launcher_logs.json: 1,784 emitters of the Launched topic, blocks 67.9M-83.48M):
is the copy address = CREATE(recipient-in-event, nonce k) for small k?  (i.e. did the launch's own wallet deploy the copy?)"""
import json, collections, rlp
from eth_utils import keccak, to_bytes
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/"
def create_addr(a, n): return "0x" + keccak(rlp.encode([to_bytes(hexstr=a), n]))[12:].hex()
o = json.load(open(S + "other_launcher_logs.json"))
res = collections.Counter(); ex = []
for x in o:
    r = "0x" + x["topics"][1][-40:]; c = x["address"].lower()
    k = next((n for n in range(6) if create_addr(r, n) == c), None)
    res[k] += 1
    if len(ex) < 4: ex.append((c, r, k, int(x["blockNumber"], 16), x["transactionHash"]))
print("copies", len(o), "copy == CREATE(event recipient, nonce k):", dict(res))
for e in ex: print(e)
# original launcher
print("original 0x3194e326 == CREATE(0x3b11cafa, 0)?", create_addr("0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5", 0))
