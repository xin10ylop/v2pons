"""Stage 6: the operator's reaction on the pools of this slice (the reaction angle measured nothing). For every pool of the current regime
('cur' 04:30-09:37 and 'late' 21:31-22:47 UTC): every buy that is not the bot's (router 0x1cbaf24d c1120e3d), with its wallet, size, offset
from L and from T, and the first pull (ModifyLiquidity < 0) after it within L+200. Wallets seen in >= 5 pools are 'recurring'.
Dust = < 0.00003 ETH."""
import pickle, collections
from lib import *
CUR0 = 85553521; FINDER_START = 85728764; FINDER_LAST = 86150251
P = pickle.load(open("parsed.pkl", "rb"))["pools"]
def regime(p): return "old" if p["L"] < CUR0 else ("cur" if p["L"] < FINDER_START else ("late" if p["L"] > FINDER_LAST else "FINDER"))
G = [p for p in P if regime(p) in ("cur", "late")]
cnt = collections.Counter()
for p in G:
    for w in {s["eoa"] for s in p["sw"] if s["buy"] and not s["bot"]}: cnt[w] += 1
print(f"pools {len(G)}; non-bot buyer wallets: {len(cnt)}; recurring (>= 5 pools): {[(w[:10], n) for w, n in cnt.most_common() if n >= 5]}")
pre = []; post = []; nofetch = [0]
for p in G:
    pulls = sorted(m["off"] for m in p["ml"] if m["dL"] < 0)
    for s in p["sw"]:
        if not s["buy"] or s["bot"]: continue
        if not s["have_tx"]: nofetch[0] += 1; continue
        eth = s["q"] / 1e18; nxt = next((x for x in pulls if x >= s["off"]), None)
        row = (regime(p), p["L"], s["eoa"][:10], round(eth, 6), s["off"], None if p["T"] is None else s["off"] - p["T"], nxt, None if nxt is None else nxt - s["off"], cnt[s["eoa"]] >= 5, s["to"][:10])
        (pre if p["T"] is None or s["off"] < p["T"] else post).append(row)
def tab(rows, label):
    print(f"\n{label}: {len(rows)}")
    by = collections.Counter((r[2], r[8], r[3] >= 0.00003) for r in rows)
    for (w, rec, nd), n in by.most_common(15): print(f"   {w} recurring={rec} non-dust={nd}: {n}")
    nd = [r for r in rows if r[3] >= 0.00003 and not r[8]]
    print(f"   non-dust, non-recurring: {len(nd)}")
    for r in nd: print("     ", r)
    lags = sorted(r[7] for r in nd if r[7] is not None)
    print(f"   their pull lags: {lags}  (no pull within L+200: {sum(1 for r in nd if r[7] is None)})")
tab(pre, "buys before T (not the bot)")
tab(post, "buys after T (not the bot; swaps up to L+120 only, their txs were fetched)")
print("buys after L+120 not attributed (tx not fetched):", nofetch[0])
pulled = [p for p in G if p["pull"] is not None]
print(f"\npools pulled within L+200: {len(pulled)} of {len(G)}: offsets from L {sorted(p['pull'] for p in pulled)}; from T {sorted(p['pull'] - p['T'] for p in pulled if p['T'] is not None)}")
