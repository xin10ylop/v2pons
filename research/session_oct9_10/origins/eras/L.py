"""era study helpers: launch table from launcher logs + txs"""
import sys, json, os, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post, rpc, batch, logs, PM, T_SWAP, T_ML, T_INIT, W, sgn, keccak
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
D = S + "origins/eras/"
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
def a32(t): return "0x" + t[-40:]
def launches():
    LG = json.load(open(S + "ops/launcher_logs.json")); TX = json.load(open(S + "ops/launcher_txs.json"))
    out = []
    for l in LG:
        h = l["transactionHash"]; t = TX.get(h)
        if not t: continue
        out.append({"h": h, "bn": int(l["blockNumber"], 16), "creator": a32(l["topics"][1]), "token": a32(l["topics"][2]), "pid": l["topics"][3],
                    "from": t["from"], "nonce": t["nonce"], "value": t["value"] / 1e18, "tip": t.get("tip"), "gas": t["gas"]})
    out.sort(key=lambda x: x["bn"])
    return out
_TM = None
def T(bn):
    """approx UTC time of a block (linear interpolation on 500k-block grid)"""
    global _TM
    if _TM is None: _TM = sorted((int(k), v) for k, v in json.load(open(D + "tsmap.json")).items())
    for (b0, t0), (b1, t1) in zip(_TM, _TM[1:]):
        if b0 <= bn <= b1: return time.strftime("%m-%d %H:%M", time.gmtime(t0 + (bn - b0) * (t1 - t0) / (b1 - b0)))
    b0, t0 = _TM[-1]; return time.strftime("%m-%d %H:%M", time.gmtime(t0 + (bn - b0) * 0.1))
