#!/usr/bin/env python3
"""Checks for follow.py, from its cache: (1) v4math against our real relay fills on Oct 8 (buy tokens at the chain state just before
our buy; sell ETH at the state just before our sell); (2) the feed replay's price (tx.value, receipt liquidity) against the chain's
sqrtP after the trigger's swap; (3) whether the 1/sqrtP additivity and the exact replay differ anywhere."""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from follow import s128, RELAY, PM, T_SWAP, T_ML, W, sgn, pool_from_receipt, net_of_fee, CACHE
data = pickle.load(open(CACHE, "rb"))
J = json.load(open(os.path.join(HERE, "follow.json")))
print("1. v4math against our real relay fills on Oct 8 (orig pools)")
for p in data["orig"]:
    L = data["launch"][p["pid"]]; pool = pool_from_receipt(L["rec"]); fee = pool["fee"]
    ls = sorted([l for l in L["logs"] if l["topics"][0] == T_SWAP], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    prev = (pool["sqrt_p"], pool["liq"])
    for l in ls:
        d = l["data"]; a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
        if l["topics"][2][-40:] == RELAY:
            if a0 < 0:
                pred = v4math.buy_out_int(prev[0], prev[1], -a0, fee); print(f"  {p['block']} buy  tokens real {a1} pred {pred} rel {(pred - a1) / a1:+.2e}")
            elif -a1 > 0:
                pred = v4math.sell_out_int(prev[0], prev[1], -a1, fee); print(f"  {p['block']} sell eth    real {a0} pred {pred} rel {(pred - a0) / max(a0, 1):+.2e}  (L before {prev[1]})")
            else:
                print(f"  {p['block']} sell into the pulled pool: 0 ETH out (L before {prev[1]})")
        prev = (W(d, 2), W(d, 3))
print("\n2. the feed replay's sqrtP after the trigger transaction vs the chain's sqrtP after the trigger's own swap")
for r in J["launches"]:
    if not r.get("trigger_tx"):
        continue
    L = data["launch"][r["pid"]]
    sw = [l for l in L["logs"] if l["topics"][0] == T_SWAP and l["transactionHash"] == r["trigger_tx"]]
    if not sw or not r.get("expected_from_feed_vs_chain_through_fire_block"):
        print(f"  {r['block']}: trigger swap in pool: {bool(sw)}; priced: {bool(r['results'])}"); continue
    chain_sp = W(sw[0]["data"], 2); feed_sp = r["expected_from_feed_vs_chain_through_fire_block"]["feed_sqrtP_after_trigger_tx"]
    blk_sp = r["expected_from_feed_vs_chain_through_fire_block"]["chain_sqrtP_after_fire_block"]
    print(f"  {r['block']} +{r['trigger_offset']}: feed/chain-after-trigger-swap {feed_sp / chain_sp - 1:+.2e}; chain after whole fire block / after trigger swap {blk_sp / chain_sp - 1:+.2e}")
print("\n3. additivity vs exact replay (max |difference| of ret over all variants)")
mx = 0; where = None
for r in J["launches"]:
    if not r["results"]:
        continue
    for s, R in r["results"].items():
        for v, x in R.items():
            if "ret_exact_replay" in x:
                d = abs(x["ret_exact_replay"] - x["ret"])
                if d > mx: mx, where = d, (r["block"], s, v)
print(f"  max {mx:.2e} at {where}")
