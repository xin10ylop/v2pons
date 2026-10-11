import json
from krpc import *
addrs = {"curve_bf44": "0xbf44f330336cf8ef89de11a5b5bd1bb5e9284e67", "token_d564": "0xd56478bb2851dbe4264cf53ee2dd834f7c7bd2b9",
         "router_e33e": "0xe33e9e479df8802cb0866d5d05258bec4cf62948", "feeto_31ea": "0x31ea5b453a6cd60f36203830de046ff32dec2cdb",
         "factory": "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e", "curve_old_f993": "0xf99324b782d31df2e60103935e29907e7c99fdd2",
         "router_9dcc": "0x9dcceb091218cdedbc2875514386615a8ce63961"}
r = batch([("eth_getCode", [a, "latest"]) for a in addrs.values()])
out = {}
for (k, a), c in zip(addrs.items(), r):
    out[k] = {"addr": a, "len": (len(c) - 2) // 2, "code": c}
    print(k, a, (len(c) - 2) // 2, c[:120])
json.dump(out, open(os.path.join(DATA, "codes.json"), "w"))
