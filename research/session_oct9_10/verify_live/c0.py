import sys; sys.path.insert(0, '..')
from chain import rpc, batch
import time, calendar
W="0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
latest=int(rpc("eth_blockNumber",[]),16); print("latest",latest)
print(rpc("eth_getTransactionCount",[W,"latest"]))
try: print(rpc("eth_getTransactionCount",[W,hex(83350000)]))
except Exception as e: print("hist nonce err", e)
for b in (83279856, 83402530):
    print(b, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(rpc("eth_getBlockByNumber",[hex(b),False])["timestamp"],16))))
