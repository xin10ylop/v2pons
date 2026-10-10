"""turn hist_inits.json + hist_opc.json (opC pools of Oct 7, before the census window) into census-shaped rows (pools, events, txs) so that
analyse.py's code prices them the same way. Writes hist_pools.json, hist_events.json, hist_txs.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import T_SWAP, T_ML, W, sgn
c = json.load(open(os.path.join(HERE, "hist_inits.json"))); H = json.load(open(os.path.join(HERE, "hist_opc.json")))
inits = {k["pid"]: k for v in c.values() for k in v["keep"]}
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
P, E, T = {}, {}, {}
T0_BN, T0_TS = 83_520_210, 1791484848          # census window start (Oct 8 18:20:48 UTC)
for pid, ls in H["ev"].items():
    k = inits[pid]; lt = H["ltx"][k["tx"]]
    sw, pulls, adds, zm = [], [], [], []
    for l in sorted(ls, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16); d = l["data"]; snd = "0x" + l["topics"][2][-40:]
        if l["topics"][0] == T_SWAP:
            sw.append({"bn": bn, "ti": ti, "li": li, "sender": snd, "a0": s128(W(d, 0)), "a1": s128(W(d, 1)), "sqrt_p": W(d, 2), "liq": W(d, 3), "tick": sgn(W(d, 4)), "fee": W(d, 5), "tx": l["transactionHash"]})
        else:
            r = {"bn": bn, "ti": ti, "li": li, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dl": sgn(W(d, 2)), "sender": snd, "tx": l["transactionHash"]}
            (pulls if r["dl"] < 0 else adds if r["dl"] > 0 else zm).append(r)
    pt = H["tx"].get(pulls[0]["tx"]) if pulls else None
    P[pid] = {"pid": pid, "token": k["token"], "fee": k["fee"], "tick_spacing": k["ts"], "sqrt_p0": k["sqrt_p"], "tick0": k["tick"], "launch_block": k["bn"],
              "launch_ts": int(T0_TS - (T0_BN - k["bn"]) * 0.1026), "launch_tx": k["tx"], "launch_from": lt["from"], "launch_nonce": lt["nonce"],
              "launch_value_eth": round(lt["value"] / 1e18, 6), "first_pull_from": pt["from"] if pt else None, "first_pull_to": pt["to"] if pt else None,
              "first_pull_selector": pt["sel"] if pt else None, "known": "none"}
    E[pid] = {"pid": pid, "launch_block": k["bn"], "swaps": sw, "pulls": pulls, "adds": adds, "zero_mods": zm}
for h, t in H["tx"].items():
    T[h] = {"hash": h, "from": t["from"], "to": t["to"] or None, "nonce": t["nonce"], "value_wei": t["value"], "selector": t["sel"], "calldata_len": t["len"], "input": t["input"]}
for k in inits.values():
    if k["pid"] in P:
        lt = H["ltx"][k["tx"]]; T[k["tx"]] = {"hash": k["tx"], "from": lt["from"], "to": lt["to"], "nonce": lt["nonce"], "value_wei": lt["value"], "selector": lt["sel"], "calldata_len": lt["len"], "input": None}
for n, o in (("hist_pools.json", P), ("hist_events.json", E), ("hist_txs.json", T)): json.dump(o, open(os.path.join(HERE, n), "w"))
print(len(P), "pools", sum(len(e["swaps"]) for e in E.values()), "swaps", len(T), "txs")
