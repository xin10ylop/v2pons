#!/usr/bin/env python3
"""linehist.py CHAIN NAME: one line's life over every census day in out/ (the lines below, by venue, fee, launch size and launch route):
pulled pools a day, its launch wallets' nonces, the median minutes to the pull, and the early round trips on it (entered within 20 s): by
the D65 crew's routers, by anyone else at a real stake (0.001+), their wins and profit. Read-only (reads out/ only)."""
import sys, os, glob, json, collections, statistics as st

LINES = {"v3_1eth": lambda p: p["venue"] == "v3" and p.get("fee") == 3000 and 0.8 <= (p.get("nat_in") or 0) <= 1.2
                    and p.get("to") == "0x73991a25c818bf1f1128deaab1492d45638de0d3",
         "v2_2eth_26605f32": lambda p: p["venue"] == "v2" and 1.7 <= (p.get("nat_in") or 0) <= 2.3 and p.get("to") == "0x26605f322f7ff986f381bb9a6e3f5dab0beaeb09",
         "v2_1eth_op3": lambda p: p["venue"] == "v2" and 0.9 <= (p.get("nat_in") or 0) <= 1.1 and p.get("to") == "0x89e5db8b5aa49aa85ac63f691524311aeb649eba"}
D65 = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}

ch, name = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
keep = LINES[name]
print(f"{ch} {name}: day | pools pulled | launch nonce | pull min (median) | D65 trips won pnl (stake) | others at a real stake: trips won pnl wallets")
for f in sorted(glob.glob(os.path.join(here, f"out/{ch}_2*_00.json"))):
    day = os.path.basename(f)[len(ch) + 1:len(ch) + 9]
    c = json.load(open(f))["chains"][ch]
    ps = {p["id"]: p for p in c["rugs"] if keep(p)}
    rt = f.replace(f"/{ch}_", f"/rt_{ch}_")
    if not ps:
        continue
    early = [t for t in json.load(open(rt))["early"] if t["pool"] in ps] if os.path.exists(rt) else []
    d = [t for t in early if t.get("via") in D65]
    o = [t for t in early if t.get("via") not in D65 and t["paid"] >= 0.001 and t.get("who")]
    print(f"  {day} | {len(ps):4d} | {collections.Counter(p.get('nonce') for p in ps.values()).most_common(2)} | {st.median(p['pull_min'] for p in ps.values()):6.1f} |"
          f" D65 {len(d):3d} {sum(t['pnl'] > 0 for t in d):3d} {sum(t['pnl'] for t in d):+.4f} ({st.median(t['paid'] for t in d) if d else 0:.4f}) |"
          f" others {len(o):3d} {sum(t['pnl'] > 0 for t in o):3d} {sum(t['pnl'] for t in o):+.4f} {len({t['who'] for t in o})}")
