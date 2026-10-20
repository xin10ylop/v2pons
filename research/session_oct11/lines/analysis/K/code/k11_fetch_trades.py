"""every curve-type event chain-wide (Buy/Sell/extra-fee/fee-distribution/e4b7) from the census window start to head, compact JSONL by 20k-block chunk;
plus the factory creates after the census window. Resumable."""
import json, os, time
from krpc import *
T = {"0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455": "B", "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df": "S",
     "0x3bc39a5562b28f5fe8f36cecabfbaa12bb969acf05717994709225fc412a9934": "X", "0x9f4cd7c4ed99d08a797804560c9c5d71d2cf7e101f2e3b5e7d1ca8a24c370e4f": "D",
     "0xe4b7e48fbd47c2f602bacadee76ad33b16542ddb4997cfc0de04c311adcfa8c7": "E"}
F = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"; CT = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"
P = os.path.join(DATA, "trades.jsonl"); PC = os.path.join(DATA, "creates_new.jsonl"); PD = os.path.join(DATA, "trades_done.json")
A0 = 79984897; STEP = 20000
head = int(rpc("eth_blockNumber", []), 16)
done = json.load(open(PD)) if os.path.exists(PD) else []
t0 = time.time()
for a in range(A0, head, STEP):
    if a in done: continue
    b = min(head, a + STEP - 1)
    L = logs({"topics": [list(T)]}, a, b, maxspan=STEP)
    rows = [[int(l["blockNumber"], 16), int(l["logIndex"], 16), l["transactionHash"], l["address"], T[l["topics"][0]], [A(x) for x in l["topics"][1:]],
             [W(l["data"], i) for i in range((len(l["data"]) - 2) // 64)]] for l in L]
    jl_append(P, rows)
    if a >= 85881750 - STEP:
        C = logs({"address": F, "topics": [CT]}, max(a, 85881751), b)
        jl_append(PC, [{"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "token": A(l["topics"][1]), "curve": A(l["topics"][2]),
                        "creator": A(l["topics"][3]), "w": [W(l["data"], k) for k in range(3)]} for l in C])
    done.append(a); json.dump(done, open(PD, "w"))
    if len(done) % 20 == 0: print(time.strftime("%H:%M:%S"), a, len(done), f"{time.time() - t0:.0f}s", STATS, flush=True)
print("done", head, STATS)
json.dump({"head": head}, open(os.path.join(DATA, "trades_head.json"), "w"))
