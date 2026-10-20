"""Extras: pull offset after the first stranger/our buy, per class; the 3.0 trap pulls after the first early buy (Oct 11 12-18);
distinct D65/DFD wallets per period (fresh vs recurring); the bot's first-buy size in our pools vs others in the same hours."""
import json, pickle, collections, time, statistics as st
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
def pc(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))] if v else None
def pkey(s): return (s[3:5], s[6:])
def first_front(p, big=0.001):
    Tli = p["T_li"]
    a = [s for s in p["sw"] if s["buy"] and s["who"] in ("ours", "w") and s["q"] >= int(big * 1e18) and (Tli is None or (s["bn"], s["li"]) < Tli) and (Tli is not None or s["off"] <= 60)]
    return a
print("== pull offset after the first front buy (>= 0.001 ETH), p10/50/90, pools pulled within 1200 blocks")
for line in ("2.433", "3.0"):
    for per in sorted(set(p["period"] for p in pools), key=pkey):
        grp = collections.defaultdict(list)
        for p in pools:
            if p["line"] != line or p["period"] != per: continue
            a = first_front(p)
            if not a: continue
            who = "US" if any(s["who"] == "ours" for s in a) else ("D65" if a[0]["to"] == R65 else "DFD" if a[0]["to"] == RFD else "OTHER")
            f = next((s for s in a if s["who"] == "ours"), a[0])
            grp[who].append((p["pull"] - f["off"]) if p["pull"] is not None else None)
        for who, v in grp.items():
            w = [x for x in v if x is not None]
            print(f"  {line} {per} {who:5s} n {len(v):4d} pulled {len(w):4d} | pull - first front buy p10/50/90 {pc(w,.1)}/{pc(w,.5)}/{pc(w,.9)}")
print("\n== 3.0 Oct 11 12:00-24:00: every pool with a buy >= 0.001 ETH before the bot (or no bot buy): first buyer, its offset, size, pull, lag")
for p in sorted(pools, key=lambda p: p["ts"]):
    if p["line"] != "3.0" or p["ts"] < 1791590400 + 86400 + 12 * 3600: continue
    a = first_front(p)
    if not a: continue
    f = a[0]; who = "US" if f["who"] == "ours" else f["eoa"][:10] + " via " + f["to"][:10]
    print(f"  {utc(p['ts'])} first {who:25s} +{f['off']} {f['q']/1e18:.5f} T {p['T']} pull +{p['pull']} lag {p['pull'] - f['off'] if p['pull'] is not None else None}")
print("\n== distinct wallets buying through D65 / DFD (any size, ahead of or after T), per 6-hour period: fresh (nonce <= 1 at the buy) / recurring")
for per in sorted(set(p["period"] for p in pools), key=pkey):
    c = collections.defaultdict(set)
    for p in pools:
        if p["period"] != per: continue
        for s in p["sw"]:
            if s["buy"] and s["to"] in (R65, RFD):
                c[(p["line"], "D65" if s["to"] == R65 else "DFD", "fresh" if (s["nonce"] or 0) <= 1 else "recurring")].add(s["eoa"])
    if c: print(f"  {per}: " + ", ".join(f"{k[0]} {k[1]} {k[2]} {len(v)}" for k, v in sorted(c.items())))
allf = set(); allr = set()
for p in pools:
    for s in p["sw"]:
        if s["buy"] and s["to"] in (R65, RFD): (allf if (s["nonce"] or 0) <= 1 else allr).add(s["eoa"])
print("  total fresh", len(allf), "recurring", len(allr), sorted(w[:10] for w in allr))
print("\n== the bot's first-buy size (ETH) in our pools vs pools without us, same hours (2.433), p10/50/90")
def hr(ts): g = time.gmtime(ts); return f"Oct{g.tm_mday} {g.tm_hour:02d}"
hrs = sorted(set(hr(p["ts"]) for p in pools if p["ours"] and p["line"] == "2.433"), key=lambda s: (s[3:5], s[6:]))
A = [p["T_q"] / 1e18 for p in pools if p["line"] == "2.433" and hr(p["ts"]) in hrs and p["ours"] and p["T_q"]]
B = [p["T_q"] / 1e18 for p in pools if p["line"] == "2.433" and hr(p["ts"]) in hrs and not p["ours"] and p["T_q"]]
print(f"  ours n {len(A)} {pc(A,.1):.4f}/{pc(A,.5):.4f}/{pc(A,.9):.4f}, mean {st.mean(A):.4f}; others n {len(B)} {pc(B,.1):.4f}/{pc(B,.5):.4f}/{pc(B,.9):.4f}, mean {st.mean(B):.4f}")
