#!/usr/bin/env python3
"""The family fingerprint, level by level, over the census's 5,164 v4 ETH pools (Oct 8 00:00 - Oct 9 14:48 UTC): how many pools each
level matches, how many of them are outside the family as the census defined it (PM, ac9650d8, 1,444 bytes, fee 1%, ts 200, 3.0 ETH), and
the behaviour of the matched pools from their logs (first buy >= 0.0002 ETH, second buy, first sell, pull). Also the sister families'
constants, to show what separates them.   python3 fingerprint.py   (writes vbot/fingerprint.json)"""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
from launch_decode import decode_1444, decode_launch
from vbot_feed import launch_of, FAMILY, POSITION_MANAGER
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
def s256(x): return x - (1 << 256) if x >> 255 else x
def s128(x):
    x = s256(x); return x - (1 << 128) if x >= (1 << 127) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)

R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
TX = pickle.load(open(os.path.join(HERE, "cache_launch.pkl"), "rb"))
PL = pickle.load(open(os.path.join(SCR, "others", "cache_plogs.pkl"), "rb"))
fam = lambda r: (r["to"] or "").lower() == "0x" + POSITION_MANAGER and r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0


def tx_of(r):
    t = TX.get(r["tx"])
    if t is None: return None
    return (t["to"] or "")[2:].lower(), int(t["value"], 16), bytes.fromhex(t["input"][2:]), t


LEVELS = [
    ("L1 to=PositionManager, selector ac9650d8", lambda to, v, d, t: to == POSITION_MANAGER and d[:4].hex() == "ac9650d8"),
    ("L2 + calldata 1,444 bytes", lambda to, v, d, t: to == POSITION_MANAGER and d[:4].hex() == "ac9650d8" and len(d) == 1444),
    ("L3 + the 1,444 layout (init + mint/settle_pair/sweep)", lambda to, v, d, t: to == POSITION_MANAGER and decode_1444(d) is not None),
    ("L4 + key: ETH/token, fee 1%, ts 200, no hook, full range", lambda to, v, d, t: launch_of(to, 3 * 10**18, d, strict=False) is not None),
    ("L5 + value 3.0 ETH", lambda to, v, d, t: launch_of(to, v, d, strict=False) is not None),
    ("L6 + sqrtP and liquidity pinned (strict)", lambda to, v, d, t: launch_of(to, v, d, strict=True) is not None),
    ("L6' strict key/price/liquidity, any value", lambda to, v, d, t: launch_of(to, 3 * 10**18, d, strict=True) is not None),
]


def behaviour(r):
    b0 = r["b0"]; buys = []; sells = []; pull = None
    for bn, li, t0, snd, d, th in sorted(PL.get(r["pid"], []), key=lambda x: (x[0], x[1])):
        if t0 == T_SWAP:
            a0 = s128(W(d, 0))
            if a0 <= -2 * 10**14: buys.append(bn - b0)
            elif a0 >= 2 * 10**14: sells.append(bn - b0)
        elif s256(W(d, 2)) < 0 and pull is None: pull = bn - b0
    return {"b1": buys[0] if buys else None, "b2": buys[1] if len(buys) > 1 else None, "s1": sells[0] if sells else None, "pull": pull,
            "sell_before_b2": bool(sells and len(buys) > 1 and sells[0] < buys[1]), "pull_before_b2": pull is not None and (len(buys) < 2 or pull <= buys[1])}


def q(v):
    v = sorted(x for x in v if x is not None)
    return [v[int(p * (len(v) - 1))] for p in (0, .1, .25, .5, .75, .9, 1)] if v else None


out = {"levels": {}}
rows = [(r, tx_of(r)) for r in R if (r["to"] or "").lower() == "0x" + POSITION_MANAGER]
print("census pools", len(R), "| launched by a PositionManager call", len(rows), "| family (census definition)", sum(1 for r in R if fam(r)))
for name, f in LEVELS:
    m = [r for r, x in rows if x and f(*x)]
    nf = [r for r in m if not fam(r)]
    out["levels"][name] = {"match": len(m), "family": len(m) - len(nf), "non_family": len(nf),
                           "non_family_kinds": collections.Counter(f"fee {r['fee']} ts {r['ts']} value {round(r['value'] or 0, 3)} len {r['inlen']}" for r in nf).most_common(6)}
    print(f"{name:62s} match {len(m):5d}  family {len(m) - len(nf):4d}  non-family {len(nf):4d}  {out['levels'][name]['non_family_kinds'][:4]}")
# pools outside PM that match key/fee/ts (other launch routes): would the fingerprint catch them? (no: to must be PM)
oth = [r for r in R if (r["to"] or "").lower() != "0x" + POSITION_MANAGER and r["fee"] == 10000 and r["ts"] == 200]
print("pools with fee 1% / ts 200 launched other ways:", len(oth), collections.Counter(((r["to"] or "")[:10], r["sel"], r["inlen"], round(r["value"] or 0, 3)) for r in oth).most_common(5))
# sister families: what their constants are
print("\nsister families' constants (decoded):")
for name, f in (("v3.0", fam), ("v5.0", lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 5.0),
                ("v2.433", lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 2500 and r["ts"] == 50),
                ("fee1%-ts200-value0", lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and not (r["value"] or 0))):
    ds = [(decode_1444(x[2]), x[1], x[3]) for r, x in rows if x and f(r)]
    c = collections.Counter((d["sqrt_p"], d["liq"], d["lo"], d["hi"], v) for d, v, t in ds if d)
    print(f"  {name:20s} n {len(ds)}  (sqrtP, L, lo, hi, value) kinds {len(c)}: {[(k[0], k[1], k[2], k[3], k[4] / 1e18, n) for k, n in c.most_common(3)]}")
    print(f"  {'':20s} gas {collections.Counter(int(t['gas'], 16) for d, v, t in ds).most_common(2)}  nonce {collections.Counter(int(t['nonce'], 16) for d, v, t in ds).most_common(4)}")
# behaviour of the strict matches
B = [behaviour(r) for r, x in rows if x and launch_of(*x[:3], strict=True)]
print(f"\nbehaviour of the {len(B)} strict matches (logs, census window +3000):")
for k in ("b1", "b2", "s1", "pull"):
    print(f"  {k:5s} min/p10/p25/med/p75/p90/max {q([b[k] for b in B])}   none: {sum(1 for b in B if b[k] is None)}")
print("  first buy offset histogram:", sorted(collections.Counter(b["b1"] for b in B if b["b1"] is not None and b["b1"] <= 40).items()))
print("  a sell >= 0.0002 before the 2nd buy:", sum(b["sell_before_b2"] for b in B), "| pull at/before the 2nd buy (or no 2nd buy before it):", sum(b["pull_before_b2"] for b in B))
out["behaviour"] = {k: q([b[k] for b in B]) for k in ("b1", "b2", "s1", "pull")}
json.dump(out, open(os.path.join(HERE, "fingerprint.json"), "w"), indent=1, default=str)
