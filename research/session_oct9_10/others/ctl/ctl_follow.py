#!/usr/bin/env python3
"""Exact FOLLOW re-pricing (yday/follow.py's price_launch, unchanged: full-block feed replay + Swap/ModifyLiquidity logs) of chosen
original-launcher (0x3194e326, call 0x2fcb9108) pools: the 9 our bot traded live on Oct 9 + one paper loser it did not trade.
Also: the crowd fingerprint of every feed buy in the replayed blocks, and our real trade (relay receipts) for comparison.
    python3 ctl_follow.py      (cache: cache_ctl.pkl next to this file)"""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, SCR); sys.path.insert(0, SCR + "/yday"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, W, sgn
import follow as F
F.STAKES = (0.0012, 0.012)
OP = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
LIVE = json.load(open(os.path.join(HERE, "live_relay.json")))
CHOSEN = ["0x2a928e9986", "0x2749b5d129", "0x43c1ce1025", "0xe444ad3734", "0xa5b3513dd4", "0x03d90ea1e1", "0xda70181865", "0x12c952fa9d",
          "0x2701d15ae9", "0x93950691e9"]
pids = [next(p for p in R if p.startswith(c) and R[p]["ours"] == "orig") for c in CHOSEN]
CACHE = os.path.join(HERE, "cache_ctl.pkl")
D = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
head = int(rpc("eth_blockNumber", []), 16)
G = {"buy_gas": 103861, "sell_gas": 103894, "sell_gas_pulled": 135200}      # follow.json meta (median of our real Oct 8 relay receipts)
for pid in pids:
    if pid in D: continue
    r = R[pid]; b0 = r["b0"]
    rec = rpc("eth_getTransactionReceipt", [r["tx"]])
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + F.LOG_SPAN, head))
    blocks = []
    for s in range(0, F.SCAN, 25):
        blocks += batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(s, min(F.SCAN, s + 25))])
    assert all(b is not None for b in blocks), pid
    D[pid] = {"rec": rec, "logs": ls, "blocks": blocks}
    pickle.dump(D, open(CACHE + ".tmp", "wb")); os.replace(CACHE + ".tmp", CACHE)
    print("fetched", pid[:12], b0, len(ls), "logs", len(blocks), "blocks", file=sys.stderr, flush=True)
# our live legs: receipts of our relay txs on these pools
lv = [x for x in LIVE["swaps"] if x["pid"] in pids]
if "live_rc" not in D:
    D["live_rc"] = dict(zip([x["tx"] for x in lv], batch([("eth_getTransactionReceipt", [x["tx"]]) for x in lv])))
    pickle.dump(D, open(CACHE, "wb"))
out = []
for pid in pids:
    r = R[pid]; L = D[pid]
    p = {"block": r["b0"], "pid": pid, "kind": "orig", "fee": r["fee"], "tx": r["tx"]}
    ours = {t["hash"] for b in L["blocks"] for t in b["transactions"] if t["from"][2:].lower() == F.WALLET}
    o = F.price_launch(p, L, G, ours)
    # crowd fingerprint: every feed buy (value > 0, token in calldata) in the replayed window, ours excluded
    token = bytes.fromhex(r["token"][2:]); bf = {}
    buys = []
    for b in L["blocks"]:
        bn = int(b["number"], 16)
        for t in b["transactions"]:
            data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16); to = (t.get("to") or "").lower()
            if to == OP or v == 0 or len(data) < 20 or token not in data: continue
            buys.append({"off": bn - r["b0"], "from": t["from"].lower(), "to": to, "inlen": len(data), "sel": "0x" + data[:4].hex(), "value": v / 1e18,
                         "prio_gwei": int(t.get("maxPriorityFeePerGas") or "0x0", 16) / 1e9, "nonce": int(t["nonce"], 16), "hash": t["hash"],
                         "ours": t["from"][2:].lower() == F.WALLET or to[2:] == F.RELAY})
    o["feed_buys"] = buys
    # deployer's txs in the window
    dep = r["from"].lower()
    o["deployer"] = dep; o["deployer_txs_in_window"] = [(int(b["number"], 16) - r["b0"], t["nonce"], (t.get("to") or "")[:12], t["input"][:10]) for b in L["blocks"] for t in b["transactions"] if t["from"].lower() == dep]
    legs = [x for x in lv if x["pid"] == pid]
    if legs:
        buy = next(x for x in legs if x["a0"] < 0); sell = next((x for x in legs if x["a0"] >= 0), None)
        gas = sum(int(D["live_rc"][x["tx"]]["gasUsed"], 16) * int(D["live_rc"][x["tx"]]["effectiveGasPrice"], 16) for x in legs) / 1e18
        X = -buy["a0"] / 1e18; Y = sell["a0"] / 1e18 if sell else 0
        o["live"] = {"buy_off": buy["bn"] - r["b0"], "sell_off": sell["bn"] - r["b0"] if sell else None, "buy_after_trigger": (buy["bn"] - r["b0"] - o["trigger_offset"]) if o.get("trigger_offset") else None,
                     "eth_in": X, "eth_out": Y, "gas_eth": gas, "ret_net": (Y - X - gas) / X, "ret_gross": (Y - X) / X}
    out.append(o)
json.dump(out, open(os.path.join(HERE, "ctl_follow.json"), "w"), indent=1, default=str)
for o in out:
    res = o["results"]; lvr = o.get("live")
    s = f"{o['block']} {o['pid'][:12]} fee {o['fee_ppm']:4d} trig +{o['trigger_offset']} pull +{o['pull_offset']} "
    if res:
        for stake in ("0.0012", "0.012"):
            s += f"| {stake}: " + " ".join(f"{k[:5]}{k[-4:]}:{v['ret']:+.4f}{v['exit'][0]}" for k, v in res[stake].items()) + " "
    else: s += str(o["skip_reason"])
    if lvr: s += f"|| LIVE buy +{lvr['buy_off']} (trig+{lvr['buy_after_trigger']}) sell +{lvr['sell_off']} net {lvr['ret_net']:+.4f}"
    print(s)
