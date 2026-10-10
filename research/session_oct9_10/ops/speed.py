import sys, time, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
head = int(rpc("eth_blockNumber", []), 16); print("head", head)
t = time.time(); bs = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(head-5000, head-4900)]); print("100 blocks", time.time()-t, sum(len(b["transactions"]) for b in bs))
for d in (100, 1000, 10000, 100000):
    try: print(d, rpc("eth_getBalance", ["0x4c45af684de8293effd3ed9654e906a7cf81ae0e", hex(head-d)]))
    except Exception as e: print(d, e)
print(rpc("eth_getTransactionCount", ["0x4c45af684de8293effd3ed9654e906a7cf81ae0e", "latest"]))
