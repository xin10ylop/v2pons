import sys, os, json; sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc
h = int(rpc("eth_blockNumber", []), 16)
for back in (100, 1000, 10000, 50000, 120000):
    try: print(back, rpc("eth_getTransactionCount", ["0x6ec9cfc5" + "0" * 0 if False else "0x4755014160c7ae63cb23b2bc0833d8a3e48e707e", hex(h - back)]))
    except Exception as e: print(back, "ERR", str(e)[:100])
for a in ("0x4755014160c7ae63cb23b2bc0833d8a3e48e707e", "0xa477fe4c2dd3514174ba6673e9b7b6b180a42555", "0x5f56ba7f2f21dc6cc38b4a1e201c57cb2c534f78", "0x60c43dbdbcb94684fbad598b65530a8500859da4"):
    print(a, "nonce now", int(rpc("eth_getTransactionCount", [a, "latest"]), 16), "bal", int(rpc("eth_getBalance", [a, "latest"]), 16) / 1e18)
