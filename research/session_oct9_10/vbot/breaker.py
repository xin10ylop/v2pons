#!/usr/bin/env python3
"""Pull exposure of the hold-30 follow on every family launch with logs (census 718 + post-census 175), from the pool logs: our buy lands at
first real buy + 1; the sell lands at the 2nd real buy + 1 (take-profit) or at our buy + 31; exposed = the pull is at or before that block.
With and without a feed-visible circuit breaker: skip a launch when the latest pull already seen in the feed (bot-router pull, i.e. the
pool's first ModifyLiquidity decrease before this launch's block) came <= 40 blocks after its own launch and <= 3,000 blocks ago.
NB the breaker's thresholds were picked after looking at this same data (in-sample).   python3 breaker.py"""
import json, pickle, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
from vbot_feed import launch_of
T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"; T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
def s(x): return x - (1 << 256) if x >> 255 else x
R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
PL = pickle.load(open(os.path.join(SCR, "others", "cache_plogs.pkl"), "rb")); RC = pickle.load(open(os.path.join(HERE, "cache_recent_logs.pkl"), "rb"))
PC = pickle.load(open(os.path.join(HERE, "cache_post_launch.pkl"), "rb"))
def info(logs, b0):
    pull = None; buys = []
    for bn, li, t0, snd, d, th in sorted(logs, key=lambda x: (x[0], x[1])):
        if t0 == T_ML and s(int(d[130:194], 16)) < 0 and pull is None: pull = bn - b0
        if t0 == T_SWAP and s(int(d[2:66], 16)) <= -2 * 10**14: buys.append(bn - b0)
    return pull, buys
rows = [(r["b0"], *info(PL.get(r["pid"], []), r["b0"]), "census") for r in R if fam(r)]
for l in PC["inits"]:
    t = PC["tx"].get(l["transactionHash"])
    if t and launch_of((t["to"] or "")[2:].lower(), int(t["value"], 16), bytes.fromhex(t["input"][2:])) and l["topics"][1] in RC:
        b0 = int(l["blockNumber"], 16); rows.append((b0, *info(RC[l["topics"][1]], b0), "post"))
rows.sort()
out = collections.Counter()
for i, (b0, pull, buys, part) in enumerate(rows):
    if not buys: out[(part, "no trigger")] += 1; continue
    buy = buys[0] + 1; sell = min(buys[1] + 1 if len(buys) > 1 and buys[1] <= buy + 30 else 10**9, buy + 31)
    exposed = pull is not None and pull <= sell
    seen = [(b, p) for b, p, *_ in rows[max(0, i - 40):i] if p is not None and b + p < b0]
    brk = bool(seen) and seen[-1][1] <= 40 and b0 - (seen[-1][0] + seen[-1][1]) <= 3000
    out[(part, "traded")] += 1; out[(part, "exposed")] += exposed
    if not brk: out[(part, "traded w/ breaker")] += 1; out[(part, "exposed w/ breaker")] += exposed
for part in ("census", "post"):
    print(f"{part:7s} traded {out[(part, 'traded')]:4d} pulled-before-our-sell {out[(part, 'exposed')]:3d}  | with breaker: traded {out[(part, 'traded w/ breaker')]:4d} exposed {out[(part, 'exposed w/ breaker')]:3d}   (no trigger {out[(part, 'no trigger')]})")
