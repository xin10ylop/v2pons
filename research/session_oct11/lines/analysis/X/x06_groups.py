"""Actors buying ahead of the bot's first buy, grouped, and the operator's reaction per pool by period and by who was ahead.
Groups: US (our relay); D65 (wallets calling the 752-byte router 0x65050a9b: fresh nonce-0/1 wallets and its recurring callers);
DFD (wallets calling its twin 0xfd1b271f); OTHER (anyone else buying >= 0.00003 ETH); dust and the sentinel 0xe71a69f4 are ignored.
Per group: its own sells (offset vs T, return), the pools it was alone in. Per pool: the pull vs T, the bot's 2nd buy, its first-buy size."""
import json, pickle, collections, statistics as st
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
DUST = int(0.00003e18)
def grp(s):
    if s["who"] == "ours": return "US"
    if s["to"] == R65: return "D65"
    if s["to"] == RFD: return "DFD"
    return "OTHER"
def pc(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))] if v else None
rows = []; sells = collections.defaultdict(list)
for p in pools:
    sw = p["sw"]; Tli = p["T_li"]; T = p["T"]
    ahead = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and s["q"] >= DUST and (Tli is None or (s["bn"], s["li"]) < Tli) and (Tli is not None or s["off"] <= 60)]
    gs = sorted(set(grp(s) for s in ahead))
    # each ahead buyer's own sell: first sell by the same wallet (ours: by the relay)
    for s in ahead:
        g = grp(s)
        mine = [x for x in sw if not x["buy"] and ((x["who"] == "ours") if g == "US" else (x["eoa"] == s["eoa"]))]
        x = mine[0] if mine else None
        sells[g].append({"period": p["period"], "line": p["line"], "eoa": s["eoa"], "nonce": s["nonce"], "q": s["q"], "off": s["off"], "T": T,
                         "sell_off": x["off"] if x else None, "sell_rel_T": (x["off"] - T) if (x and T is not None) else None,
                         "ret": (x["q"] / s["q"] - 1) if x else None, "pull": p["pull"], "pid": p["pid"]})
    after_str = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and s["q"] >= DUST and Tli is not None and (s["bn"], s["li"]) > Tli and s["off"] <= T + 60]
    pull = p["pull"]; bb = p["bot_buys"]
    second = bb[1][0] if len(bb) > 1 else None
    rows.append({"pid": p["pid"], "line": p["line"], "period": p["period"], "ts": p["ts"], "fee": p["fee"], "T": T, "T_q": p["T_q"], "pull": pull, "span": p["span"],
                 "groups": "+".join(gs) if gs else "nobody", "first_off": min((s["off"] for s in ahead), default=None),
                 "ahead_eth": sum(s["q"] for s in ahead) / 1e18, "second": second, "n_d65_5": sum(1 for s in ahead if grp(s) == "D65" and int(0.0046e18) <= s["q"] <= int(0.0053e18)),
                 "n_dfd_5": sum(1 for s in ahead if grp(s) == "DFD" and int(0.0046e18) <= s["q"] <= int(0.0053e18)),
                 "late": len(after_str), "us_q": next((s["q"] for s in ahead if grp(s) == "US"), None)})
json.dump(rows, open("x06_rows.json", "w")); json.dump(sells, open("x06_sells.json", "w"))
def reac(v):
    n = len(v); withT = [r for r in v if r["T"] is not None]
    d = [r["pull"] - r["T"] for r in withT if r["pull"] is not None]
    k = lambda a, b: sum(1 for r in withT if r["pull"] is not None and a <= r["pull"] - r["T"] <= b)
    sec = sum(1 for r in withT if r["second"] is not None and (r["pull"] is None or r["second"] < r["pull"]))
    nb = sum(1 for r in v if r["T"] is None); nbp = sum(1 for r in v if r["T"] is None and r["pull"] is not None)
    return (f"n {n:4d} T {len(withT):4d} | pull<=T+3 {k(-99,3):4d} T+4..10 {k(4,10):3d} T+11..30 {k(11,30):3d} T+31..60 {k(31,60):3d} later/none {len(withT)-k(-99,60):4d} "
            f"| pull-T p50 {pc(d,.5)} | 2nd bot buy {sec:4d} | T_q p50 {pc([r['T_q']/1e18 for r in withT], .5) or 0:.4f} | noT {nb} (pulled {nbp})")
print("=== the operator's reaction per 6-hour period and per group of buyers ahead of its bot (pulls within launch+1200)")
for line in ("2.433", "3.0"):
    for per in sorted(set(r["period"] for r in rows), key=lambda s: (s[3:5], s[6:])):
        v = [r for r in rows if r["line"] == line and r["period"] == per]
        if not v: continue
        print(f"\n{line} {per}: {len(v)} pools")
        for g, n in collections.Counter(r["groups"] for r in v).most_common():
            print(f"   {g:22s} " + reac([r for r in v if r["groups"] == g]))
print("\n=== each group's own sell, relative to the bot's first buy (T), and its return (ETH out / in - 1)")
for g, v in sells.items():
    for line in ("2.433", "3.0"):
        for per in sorted(set(x["period"] for x in v), key=lambda s: (s[3:5], s[6:])):
            w = [x for x in v if x["line"] == line and x["period"] == per]
            if not w: continue
            srt = collections.Counter(x["sell_rel_T"] for x in w).most_common(4)
            rets = [x["ret"] for x in w if x["ret"] is not None]
            print(f"  {g:5s} {line:5s} {per}: buys {len(w):4d} wallets {len(set(x['eoa'] for x in w)):4d} nonce<=1 {sum(1 for x in w if (x['nonce'] or 0) <= 1):4d} size {collections.Counter(round(x['q']/1e18,6) for x in w).most_common(2)} "
                  f"buy@ {collections.Counter(x['off'] for x in w).most_common(2)} | sold {sum(1 for x in w if x['sell_off'] is not None):4d} at T+k {srt} | ret p50 {100*pc(rets,.5) if rets else 0:+.1f}%")
