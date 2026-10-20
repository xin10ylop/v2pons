import sys, json
from krpc import *
F = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"
bn = int(rpc("eth_blockNumber", []), 16); print("head", bn)
code = rpc("eth_getCode", [F, "latest"]); print("factory code bytes", (len(code) - 2) // 2)
open(os.path.join(DATA, "factory_code.hex"), "w").write(code)
L = logs({"address": F}, bn - 2000, bn)
print("factory logs in 2000 blocks", len(L))
import collections
print(collections.Counter(l["topics"][0] for l in L).most_common())
json.dump(L, open(os.path.join(DATA, "factory_logs_2000.json"), "w"))
print(STATS)
