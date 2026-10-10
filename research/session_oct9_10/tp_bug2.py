from chain import *
head = int(rpc("eth_blockNumber", []), 16)
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0"*24 + "2abb5653352f6b2f3b4f4261877cd02d9e05a957"]}, head - int(45*60/0.103), head)
B = min(int(l["blockNumber"], 16) for l in ls if l["topics"][1].startswith("0x12c952fa9d"))
pid = [l["topics"][1] for l in ls if l["topics"][1].startswith("0x12c952fa9d")][0]
init = logs({"address": PM, "topics": [T_INIT, pid]}, B - 200, B)[0]
token = "0x" + init["topics"][3][-40:]; tb = token[2:].lower()
print("token", token, "our buy block", B)
for b in range(B - 1, B + 4):
    blk = rpc("eth_getBlockByNumber", [hex(b), True])
    for t in blk["transactions"]:
        if tb in t["input"].lower() and int(t["value"], 16) > 0:
            r = rpc("eth_getTransactionReceipt", [t["hash"]])
            print(f"  block {b - B:+d} idx {int(t['transactionIndex'],16)} from {t['from'][:10]} value {int(t['value'],16)/1e18:.6f} to {t['to'][:12]} status {r['status']} gasUsed {int(r['gasUsed'],16)} logs {len(r['logs'])}")
