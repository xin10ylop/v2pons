import json, time
from chain import *
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
A = set(json.load(open("money/pots.json"))["pots"]["A_7.01"]["crowd"])
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, head - int(6 * 3600 / 0.103), head)
pids = []
for l in ours:
    if l["topics"][1] not in pids: pids.append(l["topics"][1])
print(f"{'time':8s} {'trig':>5s} {'ours':>5s} {'pull':>5s} pull-ours pull-trig | buys before ours by non-crowd | crowd buys ours..pull")
for pid in pids:
    il = logs({"address": PM, "topics": [T_INIT, pid]}, head - int(7 * 3600 / 0.103), head)[0]; b0 = int(il["blockNumber"], 16)
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 3000, head)), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    sw = [x for x in ls if x["topics"][0] == T_SWAP]
    txs = dict(zip([x["transactionHash"] for x in sw], batch([("eth_getTransactionByHash", [x["transactionHash"]]) for x in sw])))
    B = min(int(x["blockNumber"], 16) for x in sw if x["topics"][2][-40:] == RELAY)
    pull = next((int(x["blockNumber"], 16) for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) < 0), None)
    real = [x for x in sw if s128(W(x["data"], 0)) <= -2e14 and x["topics"][2][-40:] != RELAY]
    trig = int(real[0]["blockNumber"], 16) if real else None
    pre_out = [(int(x["blockNumber"], 16) - b0, txs[x["transactionHash"]]["from"][:8], round(-s128(W(x["data"], 0)) / 1e18, 5)) for x in sw
               if int(x["blockNumber"], 16) <= B and x["topics"][2][-40:] != RELAY and txs[x["transactionHash"]]["from"].lower() not in A and s128(W(x["data"], 0)) < 0]
    crowd_after = sum(1 for x in real if B <= int(x["blockNumber"], 16) <= (pull or B + 20) and txs[x["transactionHash"]]["from"].lower() in A)
    t = time.strftime("%H:%M:%S", time.gmtime(int(rpc("eth_getBlockByNumber", [hex(B), False])["timestamp"], 16)))
    print(f"{t} +{trig - b0 if trig else '-':>4} +{B - b0:>4} +{(pull - b0) if pull else '-':>4}  {(pull - B) if pull else '-':>5}    {(pull - trig) if pull and trig else '-':>5}   | {pre_out[:3]} | {crowd_after}")
