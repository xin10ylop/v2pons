#!/usr/bin/env python3
"""Pulls with no visible outsider swap before them: every tx in [launch, pull] whose calldata mentions the token (or the pool id), with its
receipt status (a reverted outsider buy leaves no Swap log but is visible in the feed)."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from rpc2 import batch
P, TX, M = load(); BOTW, cls = classifier(TX)
D = pickle.load(open(os.path.join(HERE, "fam.pkl"), "rb"))
cases = [int(x) for x in sys.argv[1:]]
for b0 in cases:
    v = next(v for v in P.values() if v["b0"] == b0)
    tok = (v["token"] or "")[2:].lower()
    if not tok:
        lt = D["inits"].get(v["pid"]); tok = lt["topics"][3][-40:] if lt else ""
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(b0, b0 + v["pull"] + 1)], n=20)
    hits = []
    for b in blks:
        for x in b["transactions"]:
            inp = x["input"].lower()
            if (tok and tok in inp) or v["pid"][2:] in inp:
                hits.append((int(b["number"], 16) - b0, x["hash"], x["from"].lower(), (x["to"] or "").lower(), (len(inp) - 2) // 2, int(x["value"], 16) / 1e18))
    rc = batch([("eth_getTransactionReceipt", [h[1]]) for h in hits], n=20)
    print(f"\n{v['fam']} b0 {b0} token 0x{tok} pull +{v['pull']}")
    for h, r in zip(hits, rc):
        who = "DEP" if h[2] == v["dep"] else ("BOT" if h[2] in BOTW else "OTHER")
        print(f"   +{h[0]:3d} {who:5s} {h[2][:12]} -> {h[3][:12]} len {h[4]} val {h[5]:.5f} status {r['status'] if r else '?'} logs {len(r['logs']) if r else '?'}")
