"""the launch txs of the pre-window fee-100/500 candidates (not the tick-184216 family), then for the opC-shaped ones (POSM multicall, 1,444 bytes,
value 1.5-2 ETH) every Swap/ModifyLiquidity in launch..launch+3000 and the txs of every swap and pull. Cache: hist_opc.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import batch, logs, PM, T_SWAP, T_ML, W, sgn
c = json.load(open(os.path.join(HERE, "hist_inits.json")))
cands = [k for v in c.values() for k in v["keep"] if k["tick"] != 184216]
cf = os.path.join(HERE, "hist_opc.json")
H = json.load(open(cf)) if os.path.exists(cf) else {"ltx": {}, "ev": {}, "tx": {}}
need = [k["tx"] for k in cands if k["tx"] not in H["ltx"]]
if need:
    for h, t in zip(need, batch([("eth_getTransactionByHash", [h]) for h in need])):
        H["ltx"][h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2}
    json.dump(H, open(cf, "w"))
opc = [k for k in cands if H["ltx"][k["tx"]]["to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and H["ltx"][k["tx"]]["len"] == 1444]
for k in cands:
    t = H["ltx"][k["tx"]]; print(k["bn"], k["fee"], k["tick"], t["to"][:10], t["sel"], t["len"], t["value"] / 1e18, t["nonce"], t["from"][:10])
print("opC-shaped", len(opc))
for k in opc:
    if k["pid"] in H["ev"]: continue
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], k["pid"]]}, k["bn"], k["bn"] + 3000)
    H["ev"][k["pid"]] = ls
json.dump(H, open(cf, "w"))
hs = sorted({l["transactionHash"] for k in opc for l in H["ev"][k["pid"]]} - set(H["tx"]))
print("swap/pull txs to fetch", len(hs))
for h, t in zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs])):
    H["tx"][h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "sel": t["input"][2:10],
                  "len": (len(t["input"]) - 2) // 2, "input": t["input"] if len(t["input"]) < 4098 else None}
json.dump(H, open(cf, "w"))
print("done", len(H["ev"]), len(H["tx"]))
