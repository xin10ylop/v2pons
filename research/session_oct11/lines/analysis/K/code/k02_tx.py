import sys, json
from krpc import *
L = json.load(open(os.path.join(DATA, "factory_logs_2000.json")))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in L])
rc = batch([("eth_getTransactionReceipt", [l["transactionHash"]]) for l in L])
json.dump({"txs": txs, "rcpts": rc}, open(os.path.join(DATA, "create_txs_recent.json"), "w"))
for t, r in zip(txs, rc):
    print(t["hash"], "from", t["from"], "to", t["to"], "value", int(t["value"], 16) / 1e18, "sel", t["input"][:10], "len", (len(t["input"]) - 2) // 2, "gasUsed", int(r["gasUsed"], 16), "eff gp", int(r["effectiveGasPrice"], 16))
    for l in r["logs"]:
        print("   ", l["address"], l["topics"][0][:10], len(l["topics"]), (len(l["data"]) - 2) // 64, l["data"][:2 + 64 * 6] if l["topics"][0][:10] not in ("0xddf252ad", "0x8c5be1e5") else int(l["data"], 16) if len(l["data"]) > 2 else "")
