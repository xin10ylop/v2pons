"""Census: the bot's pattern after its first buy T, by line / regime / day (task 1). Untouched pools only (our wallet absent)."""
import pickle, collections
from common import *
P = pickle.load(open("cpools.pkl", "rb"))
W = 400


def grp(p):
    if p["line"] == "3.0": return f"3.0 d{p['day']}" + ("" if p["day"] < 6 else (" new" if p["ts"] >= NEW30 else " old"))
    return f"2.433 d{p['day']}"


def describe(G, label):
    n = len(G); withT = [p for p in G if p["T"] is not None]
    Ts = [p["T"] for p in withT]
    T_eth = [next(s for s in p["sw"] if s["who"] == "bot")["q"] / 1e18 for p in withT]
    b2, b2e, b3, s1, s1e, pullT, nb, before_s1 = [], [], [], [], [], [], [], 0
    mv2 = []; pr = collections.Counter(); comp = 0
    for p in withT:
        T = p["T"]; sw = [s for s in p["sw"] if T <= s["off"] <= T + W]
        bots = [s for s in sw if s["who"] == "bot"]
        sells = [s for s in sw if s["who"] == "botsell"]
        nb.append(len(bots))
        if len(bots) > 1:
            b2.append(bots[1]["off"] - T); b2e.append(bots[1]["q"] / 1e18)
            i = p["sw"].index(bots[1]); prev = p["sw"][i - 1]
            mv2.append((prev["sp"] / bots[1]["sp"]) ** 2 - 1)          # token price up = sqrtP down (ETH is currency0)
        if len(bots) > 2: b3.append(bots[2]["off"] - T)
        if sells:
            s1.append(sells[0]["off"] - T); s1e.append(sells[0]["q"] / 1e18)
            if len(bots) > 1 and sells[0]["off"] < bots[1]["off"]: before_s1 += 1
        pu = p["pull"]
        if pu is not None: pullT.append(pu - T)
        for k in (3, 10, 30, 60, 400):
            if pu is not None and pu <= T + k: pr[k] += 1
    f = lambda v: "/".join("-" if x is None else (f"{x:.3g}" if isinstance(x, float) else str(x)) for x in p1059(v))
    print(f"{label:16s} n {n:5d} T {len(withT):5d} T p10/50/90 {f(Ts):>11s} T_eth50 {pct(T_eth,.5) or 0:.3f} | bot buys in [T,T+{W}] p50 {pct(nb,.5)} "
          f"| 2nd buy n {len(b2):4d} at T+{f(b2):>11s} eth50 {pct(b2e,.5) or 0:.3f} move50 {100*(pct(mv2,.5) or 0):+.1f}% | 3rd T+{f(b3):>11s} "
          f"| 1st sell n {len(s1):4d} at T+{f(s1):>11s} eth50 {pct(s1e,.5) or 0:.4f} sell<2nd {before_s1} "
          f"| pull n {len(pullT):4d} at T+{f(pullT):>11s} by T+3/10/30/60/400: {pr[3]}/{pr[10]}/{pr[30]}/{pr[60]}/{pr[400]}")


untouched = [p for p in P if not p["ours"]]
print(f"pools {len(P)}, untouched {len(untouched)} (ours in {len(P)-len(untouched)})")
for line in ("2.433", "3.0"):
    G = [p for p in untouched if p["line"] == line]
    keys = sorted(set(grp(p) for p in G), key=lambda k: (k.split()[1], k))
    for k in keys: describe([p for p in G if grp(p) == k], k)
    describe(G, f"{line} all")
    if line == "3.0":
        describe([p for p in G if p["ts"] < NEW30], "3.0 old(<04:22)"); describe([p for p in G if p["ts"] >= NEW30], "3.0 new(>=04:22)")
# our pools (2.433): same description, for comparison
describe([p for p in P if p["ours"] and p["line"] == "2.433"], "2.433 OURS")
# coverage: how often is the 2nd bot buy beyond the 12 tx-labelled swaps (heuristic)?
for line in ("2.433", "3.0"):
    c = collections.Counter()
    for p in untouched:
        if p["line"] != line or p["T"] is None: continue
        bots = [s for s in p["sw"] if s["who"] == "bot" and p["T"] <= s["off"] <= p["T"] + W]
        c[bots[1]["src"] if len(bots) > 1 else "none"] += 1
    print(line, "2nd bot buy labelled by:", dict(c))
