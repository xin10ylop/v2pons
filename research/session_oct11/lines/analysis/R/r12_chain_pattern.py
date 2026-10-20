"""Chain, last 6 h: the bot's pattern after its first buy T by regime (task 1), the later buys' fill against their minOut, routers of big
non-bot buys (a new bot router?), and a per-pool table (r12_pools.txt)."""
import pickle, collections
from common import *
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]; botw = D["botw"]
REG = ["2.433 fee2500", "2.433 fee5000<16:28", "2.433 fee5000>=16:28", "3.0 new"]
def f(v): return "/".join("-" if x is None else (f"{x:.3g}" if isinstance(x, float) else str(x)) for x in p1059(v))
def describe(G, label):
    withT = [p for p in G if p["T"] is not None]
    Ts = [p["T"] for p in withT]; Te = [next(s for s in p["sw"] if s["who"] == "bot")["q"] / 1e18 for p in withT]
    b2, b2e, b3, s1, s1e, pullT, nb, mv2, bs_before = [], [], [], [], [], [], [], [], 0
    pr = collections.Counter(); spans = []
    for p in withT:
        T = p["T"]; spans.append(p["span"] - T)
        sw = [s for s in p["sw"] if T <= s["off"] <= T + 400]
        bots = [s for s in sw if s["who"] == "bot"]; sells = [s for s in sw if s["who"] == "botsell"]
        nb.append(len(bots))
        if len(bots) > 1:
            b2.append(bots[1]["off"] - T); b2e.append(bots[1]["q"] / 1e18)
            i = p["sw"].index(bots[1]); mv2.append((p["sw"][i - 1]["sp"] / bots[1]["sp"]) ** 2 - 1)
        if len(bots) > 2: b3.append(bots[2]["off"] - T)
        if sells:
            s1.append(sells[0]["off"] - T); s1e.append(sells[0]["q"] / 1e18)
            if len(bots) > 1 and sells[0]["off"] < bots[1]["off"]: bs_before += 1
        if p["pull"] is not None: pullT.append(p["pull"] - T)
        for k in (3, 10, 30, 60, 400):
            if p["pull"] is not None and p["pull"] <= T + k: pr[k] += 1
    nopull_noT = [p for p in G if p["T"] is None]
    print(f"{label:30s} n {len(G):3d} T {len(withT):3d} (no bot buy {len(nopull_noT)}, of them pulled {sum(1 for p in nopull_noT if p['pull'] is not None)}) T {f(Ts)} T_eth50 {pct(Te,.5) or 0:.4f}"
          f" | bot buys in [T,T+400] p50 {pct(nb,.5)} | 2nd n {len(b2)} at T+{f(b2)} eth50 {pct(b2e,.5) or 0:.3f} move50 {100*(pct(mv2,.5) or 0):+.1f}% | 3rd T+{f(b3)}"
          f" | 1st sell n {len(s1)} T+{f(s1)} eth50 {pct(s1e,.5) or 0:.4f} sell<2nd {bs_before} | pull n {len(pullT)} T+{f(pullT)} by T+3/10/30/60/400 {pr[3]}/{pr[10]}/{pr[30]}/{pr[60]}/{pr[400]} | span-T p10 {pct(spans,.1)}")
print(f"window: {utc(min(p['ts'] for p in P))} .. {utc(max(p['ts'] for p in P))} UTC; head {utc(D['head_ts'])}")
for reg in REG:
    G = [p for p in P if p["regime"] == reg]
    describe([p for p in G if not p["ours"]], reg + " untouched")
    if any(p["ours"] for p in G): describe([p for p in G if p["ours"]], reg + " OURS")
# later bot buys: output / minOut (the room a ride's buy has ahead of the bot's later buys)
for reg in REG:
    first, later = [], []
    for p in P:
        if p["regime"] != reg: continue
        bots = [s for s in p["sw"] if s["who"] == "bot" and s["minout"]]
        for k, s in enumerate(bots): (first if k == 0 else later).append(s["t"] / s["minout"])
    if first: print(f"{reg:22s} bot buy out/minOut: first n {len(first)} min {min(first):.4f} p10/50 {pct(first,.1):.4f}/{pct(first,.5):.4f}; later n {len(later)} " + (f"min {min(later):.4f} p10/50 {pct(later,.1):.4f}/{pct(later,.5):.4f}" if later else ""))
# big non-bot buys (>= 0.02 ETH) by (to, selector): a new bot router?
c = collections.Counter()
for p in P:
    for s in p["sw"]:
        if s["buy"] and s["who"] not in ("bot", "ours") and s["q"] >= 0.02e18: c[(p["line"], s["to"][:10], s["sel"], s["eoa"] in botw)] += 1
print("non-bot buys >= 0.02 ETH by (line, to, selector, from a bot wallet):", c.most_common(10))
c = collections.Counter((p["line"], s["to"][:10], s["sel"]) for p in P for s in p["sw"] if s["who"] == "bot"); print("bot buys by (to, selector):", c.most_common(5))
c = collections.Counter((p["line"], s["to"][:10], s["sel"]) for p in P for s in p["sw"] if s["who"] == "botsell"); print("bot sells by (to, selector):", c.most_common(5))
c = collections.Counter((p["line"], (p["pull_tx"] or {}).get("to", "")[:10], (p["pull_tx"] or {}).get("sel")) for p in P if p["pull"] is not None); print("first pulls by (to, selector):", c.most_common(5))
# per-pool table
rows = []
for p in sorted(P, key=lambda p: p["lb"]):
    T = p["T"]; bots = [s for s in p["sw"] if s["who"] == "bot"]; sells = [s for s in p["sw"] if s["who"] == "botsell"]
    pre = [(s["off"], round(s["q"] / 1e18, 5), s["eoa"][:10], s["to"][:10]) for s in p["sw"] if s["buy"] and s["who"] not in ("bot",) and (T is None or s["off"] <= T)]
    post = [(s["off"], round(s["q"] / 1e18, 6), s["eoa"][:10], s["to"][:10]) for s in p["sw"] if s["buy"] and s["who"] not in ("bot", "sentinel") and T is not None and s["off"] > T and s["off"] <= T + 60]
    rows.append(f"{utc(p['ts'])} {p['line']:5s} fee {p['fee']:5d} L {p['lb']} ours {int(p['ours'])} T {T} botETH {round(bots[0]['q']/1e18,4) if bots else None} bot2 {(bots[1]['off']) if len(bots)>1 else None} "
                f"botsell1 {sells[0]['off'] if sells else None} pull {p['pull']} span {p['span']} | ahead {pre} | after-T non-bot buys {post}")
open("r12_pools.txt", "w").write("\n".join(rows) + "\n")
