import json, collections
from krpc import *
F = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"
bn = int(rpc("eth_blockNumber", []), 16)
a = bn - 100000
L = logs({"address": F}, a, bn, maxspan=50000)
print("blocks", a, bn, "factory logs", len(L), collections.Counter(l["topics"][0][:10] + f"/{len(l['topics'])}/{(len(l['data'])-2)//64}" for l in L).most_common())
json.dump({"a": a, "b": bn, "logs": L}, open(os.path.join(DATA, "factory_logs_100k.json"), "w"))
for t in set(l["topics"][0] for l in L if l["topics"][0][:10] != "0x8d4aad49"):
    x = [l for l in L if l["topics"][0] == t][:2]
    for l in x: print(t[:10], l["blockNumber"], l["transactionHash"], l["topics"][1:], l["data"][:2 + 64 * 8])
