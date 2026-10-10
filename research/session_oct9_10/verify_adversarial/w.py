import sys; sys.path.insert(0, "..")
from chain import *
head = int(rpc("eth_blockNumber", []), 16)
b = rpc("eth_getBlockByNumber", [hex(head), False])
print("head", head, int(b["timestamp"],16))
import datetime
print(datetime.datetime.utcfromtimestamp(int(b["timestamp"],16)))
wal = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
print("nonce latest", int(rpc("eth_getTransactionCount", [wal, "latest"]),16))
print("bal", int(rpc("eth_getBalance", [wal, "latest"]),16)/1e18)
relay = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
print("relay bal", int(rpc("eth_getBalance", [relay, "latest"]),16)/1e18)
