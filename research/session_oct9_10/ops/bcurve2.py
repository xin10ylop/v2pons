import sys, json, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
from bcurve import getlogs
d = json.load(open(D + "bcurve_factory.json")); head = d["head"]; START = d["start"]
cre = d["logs"]
print(cre[0]["topics"], cre[0]["data"][:200])
creators = collections.Counter("0x" + l["data"][26:66] for l in cre)
print("distinct creators", len(creators), creators.most_common(5))
TL = None
# the listing event: topic0 of curve log in the f3d9 creation
TL = "0xe4b7e48fbd47c2f6"
r = rpc("eth_getTransactionReceipt", ["0xc0e9c3651fec32" + ""] ) if False else None
