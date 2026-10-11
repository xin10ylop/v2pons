"""Every log emitted by the bot's tokens (any event, any topic) over the window, in 5,000-block chunks with the list of tokens alive in that
chunk (launched within the previous 7,000 blocks). Gives every buy (PM -> recipient), every sell (seller -> PM), the bot wallets' sells
anywhere, and any non-Transfer event of the token contracts. -> logs/tok.jsonl"""
import json, pickle
from rpc import logs
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; meta = D["meta"]
f = open("cache/logs/tok.jsonl", "w"); n = 0
STEP = 5000
for a in range(meta["start"], meta["head"] + 1, STEP):
    b = min(a + STEP - 1, meta["head"])
    alive = [p["token"] for p in pools if a - 7000 <= p["L"] <= b]
    for i in range(0, len(alive), 40):
        for x in logs({"address": alive[i:i + 40]}, a, b):
            f.write(json.dumps({"addr": x["address"].lower(), "t": x["topics"], "data": x["data"], "bn": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                                "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"]}) + "\n"); n += 1
    f.flush(); print(a, b, len(alive), n, flush=True)
print("done", flush=True)
