#!/usr/bin/env python3
"""routers.py: does any pulled pool's launch contract carry the 2.433 operator's router code? Every distinct launch target (the launch
transaction's `to`) in the census files of out/, per chain, compared byte for byte with its Robinhood router 0x1cbaf24d (20,443 B; its BNB
0x07cb6161 and HyperEVM 0x948f63b2 routers are byte-identical). Read-only, public RPCs."""
import os, glob, json, collections
import hlib as H

REF = H.rpc(H.CH["rh"]["rpc"], "eth_getCode", ["0x1cbaf24d53fe930fce8eff149fa797d2611da149", "latest"])
here = os.path.dirname(os.path.abspath(__file__))
print(f"reference router code: {len(REF) // 2 - 1} B")
for ch in ("rh", "base"):
    tg = collections.Counter()
    for f in glob.glob(os.path.join(here, f"out/{ch}_2*_00.json")) + glob.glob(os.path.join(here, f"out/today_{ch}.json")):
        for p in json.load(open(f))["chains"][ch]["rugs"]:
            if p.get("to"):
                tg[p["to"]] += 1
    ts = sorted(tg)
    codes = H.batch(H.CH[ch]["rpc"], [("eth_getCode", [t, "latest"]) for t in ts], size=20, workers=3)
    hits = {t: tg[t] for t, c in zip(ts, codes) if c and c == REF}
    print(f"{ch}: {len(ts)} distinct launch contracts ({sum(tg.values())} pulled pools); with the operator's router code: {hits or 'none'}")
