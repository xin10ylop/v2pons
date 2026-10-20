"""Pool regimes for the short-exit study (offline, s02_pools.json).
ours    our relay's 5 real fills (the operator reacting to OUR position: the exact regime);
holder  an outsider bought >= 0.001 ETH from the launch to T+62 (before the pull) and had not sold by T+62 or the pull (C1R's c11 rule);
        its first such buy at offset h from T: 'early' h <= T+5 (held from about our entry), 'later' h > T+5;
bd13    0xbd9dc5f6's pools launched from Oct 12 13:15 UTC (a buy of >= 0.001 ETH; Skeptic 1's cluster), also counted in holder when it held;
none    no outside buy of >= 0.001 ETH from the launch to T+62, not ours (the router keeps buying: the contrast);
sold    an outsider >= 0.001 ETH who sold again by T+62 (2 pools in C1R; left out of both).
Usable: a router trigger T, the family's launch sqrtP and liquidity (the engine arms nothing else), not pulled by T+2, and old enough to
see our buy + 60 + 2 (age >= T + 70)."""
from sim import *
import calendar
OUT = ("recurring", "oneoff"); BD = "0xbd9dc5f684ed24f4a06559ff9dc736748cbbbc41"; T1315 = calendar.timegm((2026, 10, 12, 13, 15, 0))
SLICES = [calendar.timegm((2026, 10, 11, 1, 0, 0)) + 6 * 3600 * k for k in range(7)] + [10 ** 11]
SLICE_NAMES = ["Oct 11 01-07", "Oct 11 07-13", "Oct 11 13-19", "Oct 11 19-01", "Oct 12 01-07", "Oct 12 07-13", "Oct 12 13-14:14"]
def slice_of(ts):
    for k in range(len(SLICES) - 1):
        if SLICES[k] <= ts < SLICES[k + 1]: return SLICE_NAMES[k]
    return "before"
def classify(p):
    """(group, first holder's buy swap or None, holder sub-class)"""
    if any(s["cls"] == "ours" and s["buy"] for s in p["sw"]): return "ours", None, None
    end = min(p["T"] + 62, p["pull"] if p["pull"] is not None else 1 << 40)
    hs, sold = [], []
    for s in p["sw"]:
        if not (s["buy"] and s["cls"] in OUT and s["eth"] >= 0.001 and s["off"] <= p["T"] + 62): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        sl = [x for x in p["sw"] if not x["buy"] and x.get("from") == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end]
        (sold if sl else hs).append(s)
    if hs: return "holder", hs[0], ("early" if hs[0]["off"] - p["T"] <= 5 else "later")
    if sold: return "sold", sold[0], None
    return "none", None, None
def bd13(p):
    return p["ts"] >= T1315 and any(s["buy"] and s.get("from") == BD and s["eth"] >= 0.001 and (not p["pullpos"] or (s["bn"], s["li"]) < tuple(p["pullpos"])) for s in p["sw"])
def usable(p, D):
    if p["T"] is None: return "no trigger"
    if p["launch_sqrtP"] != SQRTP or not p["sw"] or p["sw"][0]["liq"] != LIQ: return "not the family's launch state (the engine would not arm it)"
    if p["pull"] is not None and p["pull"] <= p["T"] + 2: return "pulled by T+2"
    if D["head"] - p["lb"] < p["T"] + 70: return "too young"
    return None
