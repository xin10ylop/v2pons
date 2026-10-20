"""For tokens a wallet holds that are not the operator's Oct 8/9 launch tokens: the v4 pool(s) they trade in (Initialize log with the
token as currency1 and ETH as currency0), the launch tx's launcher/selector/deployer, and the Transfer logs of the wallet's buy."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
toks = sys.argv[1:]
head = int(rpc("eth_blockNumber", []), 16)
for t in toks:
    tt = "0x" + "0" * 24 + t[2:].lower()
    ini = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64, tt]}, 80000000, head)
    if not ini:
        # maybe token is currency0 (paired with a non-ETH) or a v2/v3 token; show code size and the first Transfer
        tr = logs({"address": t, "topics": ["0x" + keccak(text="Transfer(address,address,uint256)").hex()]}, head - 3_000_000, head)[:1]
        print(t, "no ETH v4 pool; first transfer block", int(tr[0]["blockNumber"], 16) if tr else None); continue
    l = ini[0]; tx = rpc("eth_getTransactionByHash", [l["transactionHash"]]); ts = int(rpc("eth_getBlockByNumber", [l["blockNumber"], False])["timestamp"], 16)
    print(t, "pool", l["topics"][1][:10], "block", int(l["blockNumber"], 16), time.strftime("%m-%d %H:%M", time.gmtime(ts)), "launch to", tx["to"], "sel", tx["input"][:10], "from", tx["from"][:10], "nonce", int(tx["nonce"], 16), "fee", W(l["data"], 0))
