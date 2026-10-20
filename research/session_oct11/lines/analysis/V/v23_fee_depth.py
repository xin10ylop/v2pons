"""(1) The PoolManager's protocol fee: the Swap event's fee field is 100 in some pools and 125 ppm (protocol fee 25 on) in others; which, and the
replay T+2/H60 with every swap (ours and theirs) at the fee of its time. (2) Depth and our impact at the trigger+2 entry: virtual ETH in
range (L / sqrtP), our buy's price move, the exit sell's price move, the bot's first buy's move."""
import pickle, datetime
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
pfee = {}
for p in rows:
    fs = {e[11] for e in E[p]["ev"] if e[0] == "s"}
    pfee[p] = fs
byfee = C.Counter(tuple(sorted(v)) for v in pfee.values())
d125 = C.Counter(day_of(rows[p]["launch_ts"]) for p, v in pfee.items() if v == {125}); dall = C.Counter(day_of(rows[p]["launch_ts"]) for p in rows)
print(f"(1) the Swap event fee per pool (sets of values): {dict(byfee)}; pools at 125 by launch day: {[(d, d125[d], dall[d]) for d in sorted(dall)]}")
Q = int(0.0058e18)
def replay_fee(P, a, b):
    fee = max(pfee[P.r["pool"]] or {100})
    s, L = P.state_before(a); tokens = v4math.buy_out_int(s, L, Q, fee); s = sqrt_buy(s, L, Q, fee)
    for x in P.sw:
        if x[0] < a: continue
        if x[0] >= b: break
        f = fee
        s = sqrt_buy(s, L, x[4], f) if x[3] else sqrt_sell(s, L, x[5], f)
    eth = v4math.sell_out_int(s, L, tokens, fee)
    return (eth - Q) / Q - GAS_ETH / 0.0058
base = []; adj = []; depth = []; mv_buy = []; mv_sell = []; mv_bot = []; after = 0
for pid, tb in R["trig"].items():
    P = Pool(rows[pid], E[pid]); a = tb[0] + 2; b = a + 60
    rr = P.replay(a, b, Q); pulled = rr["pulled_le"]
    base.append(-1.0 if pulled else rr["ret"]); adj.append(-1.0 if pulled else replay_fee(P, a, b)); after += max(pfee[pid] or {100}) == 125
    s, L = P.state_before(a); depth.append(L * (1 << 96) / s / 1e18)
    mv_buy.append((s / rr["s_after_ours"]) ** 2 - 1)
    se = rr["s_exit"]; s_after_sell = sqrt_sell(se, rr["L"], rr["tokens"], 100); mv_sell.append(1 - (se / s_after_sell) ** 2)
    sb, Lb = P.state_before(tb[0]); mv_bot.append((sb / sqrt_buy(sb, Lb, tb[4], 100)) ** 2 - 1)
print(f"    trades in pools at 125 ppm: {after}/{len(base)}; T+2/H60 mean {sum(base)/len(base):+.5f} -> with each pool's own fee {sum(adj)/len(adj):+.5f} (median {pct(base,0.5):+.5f} -> {pct(adj,0.5):+.5f})")
print(f"(2) virtual ETH in range at our entry p10/50/90 {p3(depth)} min {min(depth):.2f}")
print(f"    our 0.0058 ETH buy moves the price p10/50/90 {p3(mv_buy)} max {max(mv_buy):.5f}")
print(f"    our exit sell (all tokens, at the +60 state) moves it down p10/50/90 {p3(mv_sell)} max {max(mv_sell):.5f}")
print(f"    the bot's first buy moved it p10/50/90 {p3(mv_bot)}")
