"""Census: for each wallet buying after T (before the bot's 2nd buy), the pull's lag after that buy; strangers vs repeat actors."""
import pickle, collections
from common import *
P = pickle.load(open("cpools.pkl", "rb"))
lag = collections.defaultdict(list); lagS = []; base = collections.Counter()
for p in P:
    if p["T"] is None or p["ours"]: continue
    if (p["line"] == "2.433" and p["day"] == 6) or (p["line"] == "3.0" and p["day"] == 6 and p["ts"] < NEW30): continue   # pull-at-T+3 phases
    T = p["T"]; sw = p["sw"]; ib = next(i for i, s in enumerate(sw) if s["who"] == "bot")
    bots = [s for s in sw[ib + 1:] if s["who"] == "bot"]; end = bots[0]["off"] if bots else T + 60
    win = [s for s in sw[ib + 1:] if s["buy"] and s["off"] < end and s["who"] in ("x", "rep") and s["eoa"] != SENTINEL]
    by = collections.defaultdict(list)
    for s in win: by[(s["who"], s["eoa"])].append(s)
    for (who, e), ss in by.items():
        last = ss[-1]["off"]; d = None if p["pull"] is None else p["pull"] - last
        lag[(who, e)].append((d, ss[0]["q"] / 1e18, last - T))
        if who == "x": lagS.append(d)
def show(v):
    k = lambda a, b: sum(1 for x in v if x is not None and a <= x <= b)
    return f"n {len(v):4d} pull after the buy: 0-4 {k(0,4):3d}, 5-9 {k(5,9):3d}, 10-14 {k(10,14):3d}, 15-30 {k(15,30):3d}, 31-400 {k(31,400):3d}, later/never {sum(1 for x in v if x is None or x > 400):3d}"
print("strangers (one-off wallets) after T:", show(lagS))
d = [x for x in lagS if x is not None and x <= 30]; print("  lag p10/50/90 of those within 30:", p1059(d))
print("repeat actors (>= 20 line pools) after T, per wallet:")
for (who, e), v in sorted(lag.items(), key=lambda kv: -len(kv[1])):
    if who != "rep": continue
    print(f"  {e[:10]} {show([x[0] for x in v])} size50 {pct([x[1] for x in v],.5):.6f} at T+{pct([x[2] for x in v],.5)}")
