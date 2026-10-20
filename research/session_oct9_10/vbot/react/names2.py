#!/usr/bin/env python3
"""name/symbol of a time-spread sample of PM1444-family tokens (40 per family) -> names2.json"""
import sys, os, json, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from rpc2 import batch
P, TX, M = load(tx=False)
def s(x):
    try:
        b = bytes.fromhex(x[2:]); o = int.from_bytes(b[:32], 'big'); n = int.from_bytes(b[o:o + 32], 'big'); return b[o + 32:o + 32 + n].decode(errors='replace')
    except Exception: return None
out = {}
for fam in ("v3.0", "v5.0", "v2.433"):
    vs = sorted([v for v in P.values() if v["fam"] == fam and v["token"]], key=lambda v: v["b0"]); pick = vs[::max(1, len(vs) // 40)][:40]
    r = batch(sum([[("eth_call", [{"to": v["token"], "data": "0x06fdde03"}, "latest"]), ("eth_call", [{"to": v["token"], "data": "0x95d89b41"}, "latest"])] for v in pick], []), n=20)
    out[fam] = [(v["b0"], v["token"], s(r[2 * i]) if r[2 * i] else None, s(r[2 * i + 1]) if r[2 * i + 1] else None) for i, v in enumerate(pick)]
    print(fam, collections.Counter((x[2], x[3]) for x in out[fam]).most_common(12))
json.dump(out, open(os.path.join(HERE, "names2.json"), "w"), indent=0)
