"""all non-create factory events from the census window start to head (graduations etc.)"""
import json, collections
from krpc import *
F = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"
bn = int(rpc("eth_blockNumber", []), 16)
a = 79984897 - 2000000
T = ["0x" + x for x in ["cdb72f157fd3666758a6ce201387ffb52038c7562e4fff352828da1096c4b6b4", "a0a18f5bf205becee8b268d7cf69addab8548ae8ef361791464cf0e0e17c1361",
     "0a44ef75df69c534f43cd6c1aa3ef8983065fe5fe79ef9e79f6494e6f258c259", "308c390ed1ab5873392818e036cabdf408bc8ad042fbaead3108954ff75ba980",
     "bd886f85b7731f66269f57707414d435bf8df930d3357a10becc48a69377f6d5"]]
S = json.load(open(os.path.join(OUT, "k04_selectors.json")))
others = ["0x" + x for x in S["factory"]["push32"] if "0x" + x not in T and x != "8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607" and not x.startswith("ffff") and not x.startswith("0000")]
L = logs({"address": F, "topics": [T + others]}, a, bn, maxspan=1000000)
print("blocks", a, bn, "logs", len(L), collections.Counter(l["topics"][0][:10] for l in L).most_common())
json.dump({"a": a, "b": bn, "logs": L}, open(os.path.join(DATA, "factory_other_logs.json"), "w"))
