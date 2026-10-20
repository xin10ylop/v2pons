#!/usr/bin/env python3
"""name/symbol/codesize of the PM1444 family tokens (all pools in fam.pkl + recent.json) -> names.json"""
import pickle, sys, json, collections, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch
from eth_utils import keccak
D = pickle.load(open(os.path.join(HERE, "fam.pkl"), "rb")); RC = json.load(open(os.path.join(HERE, "recent.json")))
toks = {r["token"].lower(): r["fam"] for r in D["rows"].values()}
def s(x):
    try:
        b = bytes.fromhex(x[2:]); o = int.from_bytes(b[:32], 'big'); n = int.from_bytes(b[o:o + 32], 'big'); return b[o + 32:o + 32 + n].decode(errors='replace')
    except Exception: return None
out = {}
T = sorted(toks)
for i in range(0, len(T), 16):
    ch = T[i:i + 16]; calls = []
    for t in ch: calls += [("eth_call", [{"to": t, "data": "0x06fdde03"}, "latest"]), ("eth_call", [{"to": t, "data": "0x95d89b41"}, "latest"]), ("eth_getCode", [t, "latest"])]
    r = batch(calls)
    for j, t in enumerate(ch):
        c = r[3 * j + 2] or "0x"
        out[t] = {"fam": toks[t], "name": s(r[3 * j]) if r[3 * j] else None, "sym": s(r[3 * j + 1]) if r[3 * j + 1] else None, "codesize": (len(c) - 2) // 2, "codehash": keccak(bytes.fromhex(c[2:])).hex()[:16]}
json.dump(out, open(os.path.join(HERE, "names.json"), "w"))
for f in ("v3.0", "v5.0", "v2.433"):
    x = [v for v in out.values() if v["fam"] == f]
    print(f, len(x), collections.Counter((v["name"], v["sym"]) for v in x).most_common(6), collections.Counter((v["codesize"], v["codehash"]) for v in x).most_common(3))
