"""The 2.433 operator's single Ethereum-mainnet launch (Oct 12 13:51:59 UTC, hub 0x6c3bd8f6, value 2.4333285 ETH, fee 5000/ts 100):
every swap in the pool from launch to pull (Swap logs by pool id, 10-block chunks on the Blast public archive), with the token recipient
(the mainnet bot router 0xfac75d23 or someone else) and the transaction sender."""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_SWAP, T_ML, T_TRANSFER, T_INIT, W, sgn, unpad, pad
PM = "0x000000000004444c5dc75cb358380d2e3de08a90"; ROUTER = "0xfac75d23e417ee39c180bbced4c665c9b57b83b2"; TOK = "0x96e4bac509b625977bd0aa8ac52fdac854c02777"
def call(m, p, c="eth_archive"):
    for i in range(10):
        try: time.sleep(0.7); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
rc = call("eth_getTransactionReceipt", ["0x88b6b0a94532" if False else None]) if False else None
L, P = 26176810, 26176827
logs = []
for k in range(L, P + 1, 10): logs += call("eth_getLogs", [{"address": PM, "fromBlock": hex(k), "toBlock": hex(min(P, k + 9))}])
init = [l for l in logs if l["topics"][0] == T_INIT][0]; pid = init["topics"][1]
d = init["data"]; print("pool", pid, "fee", W(d, 0), "ts", sgn(W(d, 1)), "sqrtP", W(d, 3))
tr = []
for k in range(L, P + 1, 10): tr += call("eth_getLogs", [{"address": TOK, "fromBlock": hex(k), "toBlock": hex(min(P, k + 9)), "topics": [T_TRANSFER, pad(PM)]}])
rcpt = {t["transactionHash"]: unpad(t["topics"][2]) for t in tr}
for l in logs:
    if l["topics"][1] != pid: continue
    if l["topics"][0] == T_SWAP:
        tx = call("eth_getTransactionByHash", [l["transactionHash"]])
        print("swap +%d" % (int(l["blockNumber"], 16) - L), "ETH %.5f" % (-sgn(W(l["data"], 0)) / 1e18), "to", rcpt.get(l["transactionHash"]), "from", tx["from"], "nonce", int(tx["nonce"], 16), "tx.to", tx["to"], tx["input"][:10], "prio", int(tx.get("maxPriorityFeePerGas", "0x0"), 16) / 1e9)
    elif l["topics"][0] == T_ML: print("ML +%d" % (int(l["blockNumber"], 16) - L), sgn(W(l["data"], 2)))
