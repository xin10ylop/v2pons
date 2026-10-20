"""All 573 triggered pools, every swap in [trigger, trigger+100] attributed. (1) Flows in our hold window [T+2, T+62) by class and the
counterfactual replays (only the bot's swaps / only the others'). (2) The bot's sells: first sell after its first buy, count by T+100.
(3) The pull against the bot's last buy before it (pre-pull buys are fetched by the census). (4) Exit on the bot going quiet: sell at the
head of the first block after N blocks with no bot buy (N = 10/15/20/30), at the latest a + H (H = 60/90), entry T+2; the decision uses
only bot buys seen before the sell block (what the feed shows)."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
Q = int(0.0058e18)
def is_bot(x): t = T.get(x[8]); return None if t is None else t["to"] == BOT
def replay_keep(P, a, b, keep):
    s, L = P.state_before(a); tokens = v4math.buy_out_int(s, L, Q, P.fee); s = sqrt_buy(s, L, Q, P.fee)
    for x in P.sw:
        if x[0] < a: continue
        if x[0] >= b: break
        if keep(x): s = sqrt_buy(s, L, x[4], P.fee) if x[3] else sqrt_sell(s, L, x[5], P.fee)
    return (v4math.sell_out_int(s, L, tokens, P.fee) - Q) / Q - GAS_ETH / 0.0058
flows = C.Counter(); cnt = C.Counter(); full, ob, oo = [], [], []
first_sell = []; nsell100 = []; pull_after_last = []; pull_after_last_nobuy = []; unk_last = 0
exits = C.defaultdict(list)
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid]); a = tb[0] + 2; b = a + 60
    rr = P.replay(a, b, Q); pulled = rr["pulled_le"]
    full.append(-1.0 if pulled else rr["ret"])
    ob.append(-1.0 if pulled else replay_keep(P, a, b, lambda x: is_bot(x)))
    oo.append(-1.0 if pulled else replay_keep(P, a, b, lambda x: not is_bot(x)))
    for x in P.sw:
        if a <= x[0] < b:
            c = "bot" if is_bot(x) else ("unknown" if is_bot(x) is None else "other")
            flows[(c, x[3])] += x[4]; cnt[(c, x[3])] += 1
    bs = [x for x in P.sw if tb[0] <= x[0] <= tb[0] + 100 and not x[3] and is_bot(x)]
    first_sell.append(bs[0][0] - tb[0] if bs else None); nsell100.append(len(bs))
    if P.first_pull:
        lastb = [x for x in P.sw if x[0] <= P.first_pull and x[3] and is_bot(x)]
        if lastb: pull_after_last.append(P.first_pull - lastb[-1][0])
    # exit on quiet: bot buys at blocks >= T (known up to T+100)
    bb = sorted({x[0] for x in P.sw if x[3] and is_bot(x) and tb[0] <= x[0] <= tb[0] + 100})
    for H in (60, 90):
        for N in (10, 15, 20, 30, None):
            sell = a + H
            if N is not None:
                last = max([y for y in bb if y < a], default=tb[0])
                blk = a
                while blk < a + H:
                    seen = [y for y in bb if y < blk]
                    lb = seen[-1] if seen else tb[0]
                    if blk - lb > N: sell = blk; break
                    blk += 1
            x = P.replay(a, sell, Q)
            exits[(H, N)].append(-1.0 if x["pulled_le"] else x["ret"])
def s(xs): return f"n {len(xs)} mean {sum(xs)/len(xs):+.4f} med {pct(xs,0.5):+.4f} win {sum(1 for v in xs if v > 0)/len(xs):.1%} lost {sum(1 for v in xs if v == -1.0)/len(xs):.1%}"
print("(1) trig+2 / hold 60, all 573 pools:", s(full))
print("    only the bot's swaps re-applied:", s(ob))
print("    only the others' swaps re-applied:", s(oo))
for k in sorted(cnt): print(f"    flow {k[0]:8s} {'buys ' if k[1] else 'sells'} n {cnt[k]:6d} ETH {flows[k]/1e18:9.3f}")
fs = [x for x in first_sell if x is not None]
print(f"(2) pools where the bot sold in [T, T+100]: {len(fs)}/{len(first_sell)}; first bot sell at T+ p10/50/90 {p3(fs)}; inside [T+2, T+62): {sum(1 for x in fs if 2 <= x < 62)}; sells per pool by T+100 p50/p90 {pct(nsell100,0.5)}/{pct(nsell100,0.9)}")
print(f"(3) first pull minus the bot's last fetched buy before it: n {len(pull_after_last)} p10/50/90 {p3(pull_after_last)} min {min(pull_after_last)}")
print("(4) exit when no bot buy for N blocks (entry T+2):")
for (H, N), xs in sorted(exits.items(), key=lambda kv: (kv[0][0], kv[0][1] or 999)): print(f"    max hold {H} quiet N {N}: {s(xs)}")
json.dump({"pull_after_last": pull_after_last, "first_sell": first_sell}, open(os.path.join(V, "v14_bot_flow.json"), "w"))
