from chain import *
head = int(rpc("eth_blockNumber", []), 16)
pid = None
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0"*24 + "2abb5653352f6b2f3b4f4261877cd02d9e05a957"]}, head - int(40*60/0.103), head)
pids = {}
for l in ls: pids.setdefault(l["topics"][1], []).append(int(l["blockNumber"], 16))
for p, bs in pids.items():
    if p.startswith("0x12c952fa9d"):
        B = min(bs)
        sw = logs({"address": PM, "topics": [T_SWAP, p]}, B - 2, B + 4)
        for l in sw:
            t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
            a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            print(int(l["blockNumber"], 16) - B, t["from"][:10], "tx.value", int(t["value"], 16) / 1e18, "swap ETH in", -a0 / 1e18, "to", t["to"][:12], "input", t["input"][:10], "len", len(t["input"]) // 2)
