"""The replay grid on C-1 core (ETH): trigger = the first buy whose transaction went to the bot's router 0xd6d35b56 (fetched txs: first 12
swaps, the first real buy, pre-pull buys). Entries trigger+1/+2/+3 (head of block), holds 20/40/60/80/100, q = 0.0058 ETH, gas $0.02.
A pull in a block <= the sell block = -100% ("pulled_le"); "pulled_lt" counts strictly earlier blocks only."""
import pickle
from sim import *
rows = [r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"]
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); T = json.load(open(os.path.join(V, "c1_txs.json")))
Q = int(0.0058e18)
pools = {}; trig = {}; chk = []; late_add = 0; nobot = []
for r in rows:
    P = Pool(r, E[r["pool"]]); pools[r["pool"]] = P
    chk.append(P.check()); late_add += bool(P.late_adds)
    tb = None
    for x in P.sw:
        t = T.get(x[8])
        if t and t["to"] == BOT and x[3]: tb = x; break
    if tb: trig[r["pool"]] = tb
    else: nobot.append(r["pool"])
print(f"C-1 core ETH pools {len(rows)}; with a bot buy (fetched) {len(trig)} ({len(trig)/len(rows):.1%}); without {len(nobot)}")
print(f"re-simulation check (no trade): max rel sqrt error before the first pull: p50 {pct(chk,0.5):.2e} p99 {pct(chk,0.99):.2e} max {max(chk):.2e}; pools with a liquidity add after launch: {late_add}")
# frb consistency
agree = sum(1 for r in rows if r["pool"] in trig and r["frb"] and r["frb"]["to"] == BOT and r["frb"]["off"] + r["launch_block"] == trig[r["pool"]][0])
print("trigger block == census frb block (frb via bot):", agree)
res = {}
def summ(xs):
    rets = [x["ret"] if not x["pulled_le"] else -1.0 for x in xs]
    n = len(rets)
    if not n: return None
    return {"n": n, "mean": sum(rets)/n, "med": pct(rets, 0.5), "win": sum(1 for v in rets if v > 0)/n, "worst": min(rets),
            "pulled": sum(x["pulled_le"] for x in xs)/n, "pulled_lt": sum(x["pulled_lt"] for x in xs)/n, "pb_buy": sum(x["pulled_before_buy"] for x in xs)}
out = {}
for k in (1, 2, 3):
    for H in (20, 40, 60, 80, 100):
        xs = []
        for pid, tb in trig.items():
            a = tb[0] + k; x = pools[pid].replay(a, a + H, Q)
            if x is None: continue
            x["pid"] = pid; x["day"] = day_of(pools[pid].r["launch_ts"]); xs.append(x)
        s = summ(xs); out[(k, H)] = (s, xs)
        usd = s["mean"] * 15 * (len(rows) / 7) * (s["n"] / len(rows))
        print(f"entry trig+{k} hold {H:3d}: n {s['n']} mean {s['mean']:+.4f} med {s['med']:+.4f} win {s['win']:.1%} worst {s['worst']:+.3f} pulled<=sell {s['pulled']:.1%} (strictly before {s['pulled_lt']:.1%}; before our buy {s['pb_buy']}) $/day {usd:+.0f}")
pickle.dump({"trig": {k: v for k, v in trig.items()}, "nobot": nobot, "grid": {f"{k}|{h}": v[1] for (k, h), v in out.items()}}, open(os.path.join(V, "replay.pkl"), "wb"))
