#!/usr/bin/env python3
"""For follow.json: would the crowd buys our sell profits from (behind our buy, before our sell lands) still go through with our buy
ahead of them? Their Universal Router calldata carries amountOutMinimum (the word after amountIn); with our buy in, their output is
recomputed (1/sqrtP additive) and compared with it. Prints, per stake and variant, the trades whose profit relies on a crowd buy
that would revert."""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from follow import s128, RELAY, T_SWAP, W, net_of_fee, CACHE, Q96
data = pickle.load(open(CACHE, "rb")); J = json.load(open(os.path.join(HERE, "follow.json")))
slack = []; rows = collections.defaultdict(list)
for r in J["launches"]:
    if not r["results"]:
        continue
    L = data["launch"][r["pid"]]; fee = r["fee_ppm"]
    txs = {t["hash"]: t for b in L["blocks"] for t in b["transactions"]}
    sw = sorted([l for l in L["logs"] if l["topics"][0] == T_SWAP and l["topics"][2][-40:] != RELAY], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    prev = r["sqrt_p0"]; seq = []
    for l in sw:
        d = l["data"]; seq.append((int(l["blockNumber"], 16), s128(W(d, 0)), s128(W(d, 1)), prev, W(d, 2), W(d, 3), l["transactionHash"])); prev = W(d, 2)
    for stake, R in r["results"].items():
        X = int(round(float(stake) * 1e18)); xn = net_of_fee(X, fee)
        for v, x in R.items():
            if x["exit"] in ("buy_reverted", "pull_first", "pull_before_buy"):
                continue
            B, S = x["buy_block"], x["sell_land_block"]
            bad = []
            for bn, a0, a1, sp_before, sp_after, Lq, h in seq:
                if not (B < bn <= S - 1) or a0 >= 0:
                    continue
                t = txs.get(h)
                if t is None:
                    continue
                inp = t["input"][10:]; words = [inp[i:i + 64] for i in range(0, len(inp), 64)]
                amt = -a0; mo = None
                for i, w in enumerate(words[:-1]):
                    if int(w, 16) == amt:
                        mo = int(words[i + 1], 16); break
                if mo is None:
                    continue
                if stake == "0.0012" and v == "land1_fast":
                    slack.append(a1 / mo - 1 if mo else float("inf"))
                sp_ours = int(Q96 / (Q96 / sp_before + xn / Lq))
                out_with_us = v4math.buy_out_int(sp_ours, Lq, amt, fee)
                if out_with_us < mo:
                    bad.append((bn - B, amt / 1e18, round(a1 / mo - 1, 4), round(out_with_us / mo - 1, 4)))
            if bad:
                rows[(stake, v)].append((r["block"], round(x["ret"], 4), bad))
s = sorted(slack)
print(f"crowd buys behind ours (0.0012 land1_fast windows): n {len(s)}; their output over their amountOutMinimum: min {s[0]:+.4f} median {s[len(s)//2]:+.4f} max {s[-1]:+.4f}" if s else "no decodable crowd buys")
for k in sorted(rows):
    print(k, "trades whose sell relies on a crowd buy that would revert with our buy ahead:", len(rows[k]))
    for row in rows[k]:
        print("    ", row)
