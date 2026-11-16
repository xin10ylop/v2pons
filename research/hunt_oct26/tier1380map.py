#!/usr/bin/env python3
"""tier1380map.py: the 1,380 B line's liquidity tiers keyed by launch price. For every pool of the line in the dumps, its v4 Initialize
(fee, tick spacing, hooks, sqrtPriceX96) and its tier (the virtual native reserve before the first swap); prints each launch price with its
tier, pool count, and how many were pulled within 2 h. Read-only."""
import json, collections, hlib as H
from eth_utils import keccak
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]
T_INIT4 = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
lc = json.load(open("out/struct_launch_rh.json")); cc = json.load(open("out/token_code_rh.json"))
created = {}
for d in ("20261110", "20261111", "20261114", "20261115"):
    for k, tok, bn, tx, nin in json.load(open(f"out/rh_{d}_00.json"))["chains"]["rh"]["created"]:
        created[k] = tx
allp = {}
for f in ("out/dump_rh_nov1011.json", "out/dump_rh_nov1415.json"):
    allp.update(json.load(open(f))["pools"])
line = [(k, p) for k, p in allp.items() if (lambda t: t and t[1].startswith("0x58daec31") and t[2] == "0xdd46508f" and t[3] == 1380)(lc.get(created.get(k))) and cc.get(p["tok"], ["?", 0])[1] == 4655]
agg = collections.defaultdict(lambda: [0, 0, set()])
for k, p in line:
    L = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(p["bn"]), "address": PM, "topics": [T_INIT4, k[3:]]}]) or []
    if not L:
        continue
    d = L[0]["data"][2:]; fee = int(d[:64], 16); ts = H.i256(d[64:128]); hooks = "0x" + d[128 + 24:192]; sp = int(d[192:256], 16)
    ev = [e for e in p["ev"] if e[4] and e[5]]; tier = round(ev[0][4] - ev[0][2], 1) if ev else None
    a = agg[(sp, fee, ts, hooks == "0x" + "0" * 40)]; a[0] += 1; a[1] += p["pull"] is not None; a[2].add(tier)
print("sqrtPriceX96 | fee | tickSpacing | no hook | pools | pulled within 2 h | tier (virtual native before the first swap)")
for (sp, fee, ts, nohook), (n, pulled, tiers) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {sp} | {fee} | {ts} | {nohook} | {n} | {pulled} | {sorted(t for t in tiers if t is not None)}")
