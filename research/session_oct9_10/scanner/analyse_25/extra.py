"""analyse_25 extra: the deployers' activity after the census window (nonce now vs in the window; a handful of RPC calls), the F4 launch
calldata (a25a9a3d) and what the 0.000100683 ETH is, the position composition (ETH in the launch range), and the 0x06cb3a68 class's
5 real buys and 7 sells. Writes extra.json."""
import sys, os, json, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common25 import *  # noqa
import chain
P = load_pools(); T = load_txs(); M = load_blocks_meta(); F = load_families()
K = json.load(open(os.path.join(HERE, "keys.json")))
DEP06 = "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"; DEP84 = "0x843784a6d2c839ca170e64c75dcc797dfc4a86a3"; L_E1 = "0xe181b36e96e9cab0130707bcb513fc1401e0ba32"
utc = lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
out = {}
cache = os.path.join(HERE, "rpc_cache.json")
if os.path.exists(cache): R = json.load(open(cache))
else:
    head = chain.rpc("eth_blockNumber", [])
    r = chain.batch([("eth_getTransactionCount", [DEP06, "latest"]), ("eth_getTransactionCount", [DEP84, "latest"]), ("eth_getBalance", [DEP06, "latest"]), ("eth_getBalance", [DEP84, "latest"]),
                     ("eth_getBlockByNumber", [head, False])])
    rc = chain.batch([("eth_getTransactionReceipt", [P[pid]["launch_tx"]]) for pid in F[K[3]]["pids"][:2]] + [("eth_getTransactionReceipt", [P[F[K[0]]["pids"][0]]["launch_tx"]])])
    R = {"head": int(head, 16), "head_ts": int(r[4]["timestamp"], 16), "nonce06": int(r[0], 16), "nonce84": int(r[1], 16), "bal06": int(r[2], 16), "bal84": int(r[3], 16), "rcpts": rc}
    json.dump(R, open(cache, "w"))
for dep, nk in ((DEP06, "nonce06"), (DEP84, "nonce84")):
    ps = [p for p in P.values() if p["launch_from"] == dep]
    last = max(ps, key=lambda p: p["launch_block"])
    out[dep] = {"launches_in_window": len(ps), "first_utc": utc(min(p["launch_ts"] for p in ps)), "last_utc": utc(last["launch_ts"]),
                "nonce_last_launch_in_window": last["launch_nonce"], "nonce_now": R[nk], "head_utc": utc(R["head_ts"]), "balance_eth_now": R["bal06" if nk == "nonce06" else "bal84"] / 1e18,
                "per_hour": collections.Counter(utc(p["launch_ts"])[:13] for p in ps).most_common(8)}
# F4 launch: calldata words, value, receipt logs
p0 = P[F[K[3]]["pids"][0]]; t = T[p0["launch_tx"]]
inp = t.get("input") or t["input512"]
out["F4_launch_calldata_words"] = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)][:28]
out["F4_launch_value_wei"] = t["value_wei"]
def rc_summary(rc):
    o = []
    for l in rc["logs"]:
        o.append({"addr": l["address"], "t0": l["topics"][0][:10] if l["topics"] else None, "ntop": len(l["topics"]), "data_words": [l["data"][2 + 64 * i: 2 + 64 * (i + 1)] for i in range(min(6, (len(l["data"]) - 2) // 64))]})
    return {"status": rc["status"], "gasUsed": int(rc["gasUsed"], 16), "to": rc["to"], "n_logs": len(rc["logs"]), "logs": o}
out["F4_launch_receipts"] = [rc_summary(r) for r in R["rcpts"][:2]]
out["F1_launch_receipt"] = rc_summary(R["rcpts"][2])
# position composition at launch: ETH held by the launch range at the launch price
def amounts(sp, lo, hi, L):
    sa, sb = sqrt_at_tick(lo), sqrt_at_tick(hi)
    if sp <= sa: return (L * (sb - sa) * Q96 // (sa * sb), 0)
    if sp >= sb: return (0, L * (sb - sa) // Q96)
    return (L * (sb - sp) * Q96 // (sp * sb), L * (sp - sa) // Q96)
comp = {}
for k in K:
    pid = F[k]["pids"][0]; p = P[pid]; E = load_events({pid})[pid]; a = E["adds"][0]
    e0, t1 = amounts(p["sqrt_p0"], a["lo"], a["hi"], a["dl"])
    comp[k] = {"eth_wei_in_position": e0, "tokens_in_position": t1 / 1e18, "tick0": p["tick0"], "range": [a["lo"], a["hi"]], "price_eth_per_token": (Q96 / p["sqrt_p0"]) ** 2,
               "stake_tokens_at_launch_price": STAKE / 1e18 / ((Q96 / p["sqrt_p0"]) ** 2)}
out["position_composition"] = comp
# 0x06cb3a68 class: the 5 real buys and the 7 sells
E = load_events(set(p["pid"] for p in P.values() if p["launch_from"] == DEP06))
rows = []
for pid, e in E.items():
    p = P[pid]
    for s in e["swaps"]:
        tx = T.get(s["tx"]) or {}
        if tx.get("from") == "0xe71a69f434a719cd5afa411568b69716aab3b84a": continue
        rows.append({"pid": pid[:12], "off": s["bn"] - p["launch_block"], "side": "buy" if s["a0"] < 0 else "sell", "eth": abs(s["a0"]) / 1e18, "from": tx.get("from"), "to": tx.get("to"), "sel": tx.get("selector"), "nonce": tx.get("nonce")})
out["dep06_non_dust_swaps"] = sorted(rows, key=lambda r: (r["pid"], r["off"]))
json.dump(out, open(os.path.join(HERE, "extra.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:9000])
