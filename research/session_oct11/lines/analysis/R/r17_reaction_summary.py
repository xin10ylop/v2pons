"""Summary of every stranger buy after the bot's first buy (census one-off wallets, the regimes without the pull-at-T+3 phase; chain 6 h non-recurring wallets) per line:
pull lag after the buy, by size (dust < 0.00003 ETH vs larger); and the fronts (strangers before T) on the 3.0 line today."""
import pickle, collections
from common import *
C = pickle.load(open("cpools.pkl", "rb")); D = pickle.load(open("chpools.pkl", "rb"))
rows = []
for p in C:
    if p["T"] is None or p["ours"]: continue
    if p["day"] == 6 and (p["line"] == "2.433" or p["ts"] < NEW30): continue      # the pull-at-T+3 phases (every pool pulled 3 blocks after the bot)
    ib = next(i for i, s in enumerate(p["sw"]) if s["who"] == "bot")
    for s in p["sw"][ib + 1:]:
        if s["buy"] and s["who"] == "x" and s["eoa"] != SENTINEL and s["off"] - p["T"] <= 400:
            rows.append(("census", p["line"], s["eoa"], s["q"] / 1e18, s["off"] - p["T"], None if p["pull"] is None else p["pull"] - s["off"], p["day"]))
REC = {"0x93b07902", "0xb8c879dc", "0xe9d83e95", "0x7ae81404", "0x8c009ea5", "0x8cf143dd", "0xb4c345dc"}   # recurring wallets (>= 5 pools) of r14/r16
for p in D["pools"]:
    if p["T"] is None or p["ours"]: continue
    ib = next(i for i, s in enumerate(p["sw"]) if s["who"] == "bot")
    for s in p["sw"][ib + 1:]:
        if s["buy"] and s["who"] == "w" and s["eoa"][:10] not in REC:
            rows.append(("chain", p["line"], s["eoa"], s["q"] / 1e18, s["off"] - p["T"], None if p["pull"] is None else p["pull"] - s["off"], 7))
def show(v):
    k = lambda a, b: sum(1 for x in v if x is not None and a <= x <= b)
    return f"n {len(v):3d}: pulled 0-9 blocks after {k(0,9):3d}, 10-14 {k(10,14):3d}, 15-30 {k(15,30):3d}, 31-400 {k(31,400):3d}, not in window {sum(1 for x in v if x is None or x > 400):3d}"
for src in ("census", "chain"):
    for line in ("2.433", "3.0"):
        for lab, f in (("dust <0.00003", lambda q: q < 0.00003), (">=0.00003", lambda q: q >= 0.00003)):
            v = [r[5] for r in rows if r[0] == src and r[1] == line and f(r[3])]
            if v: print(f"{src:6s} {line:5s} stranger after T, {lab:13s} {show(v)}; lags {sorted(x for x in v if x is not None)[:30]}")
print("\nchain cases (non-recurring wallets after T):")
for r in rows:
    if r[0] == "chain": print("  ", r[1], r[2][:10], f"{r[3]:.6f} ETH at T+{r[4]}", "pull lag", r[5])
# per pool: the first stranger buy (>= 0.00003 ETH) after T, census, and the pull lag after it
print("\nper pool (census, first stranger buy >= 0.00003 after T):")
for line in ("2.433", "3.0"):
    v = []
    for p in C:
        if p["T"] is None or p["ours"] or p["line"] != line: continue
        if p["day"] == 6 and (p["line"] == "2.433" or p["ts"] < NEW30): continue
        ib = next(i for i, s in enumerate(p["sw"]) if s["who"] == "bot")
        st = [s for s in p["sw"][ib + 1:] if s["buy"] and s["who"] == "x" and s["eoa"] != SENTINEL and s["q"] >= 0.00003e18 and s["off"] - p["T"] <= 400]
        if st: v.append(None if p["pull"] is None else p["pull"] - st[0]["off"])
    print(f"  {line}: {show(v)}; median lag {pct([x for x in v if x is not None], .5)}")
