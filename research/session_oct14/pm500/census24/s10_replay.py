"""Step 10: exact-integer replay of our trade on every pool (v4sim, validated on all 23,495 real swaps in s06): buy q ETH at the head of
block L+a (before every swap of that block), re-apply every later real swap by its input and its own fee, sell all tokens at the head
of block L+b. A pull at or before block L+b is -100%. Reaction: the launcher pulls R blocks after our buy (the lag measured after
outside buys in s07); R = None is the no-reaction (optimistic) replay. Gas $0.02 a round trip; ETH = $2,570 (as in the census)."""
import sys, statistics
from common import *
from v4sim import Pool, sqrt_at_tick
ETH_USD = 2570.0; GAS_USD = 0.02
pools = [p for p in load_pools() if "add_off" in p]
def fee_near(p, o):
    nxt = [s["fee"] for s in p["swaps"] if s["o"] >= o]
    prv = [s["fee"] for s in p["swaps"] if s["o"] < o]
    return max(nxt[:1] + prv[-1:] + [500])
def replay(p, a, b, q_eth, R=None):
    if a <= p["add_off"] or b <= a: return None
    pull = p.get("pull_off")
    if R is not None: pull = a + R if pull is None else min(pull, a + R)
    if pull is not None and b >= pull: return -1.0
    pool = Pool(p["sqrt0"], (p["tl"], p["tu"], p["liq"]), 500)
    for s in p["swaps"]:
        if s["o"] >= a: break
        pool.sqrt = s["sqrt"]
    q = int(q_eth * 1e18)
    pool.fee = fee_near(p, a); tok = pool.buy(q)
    for s in p["swaps"]:
        if s["o"] < a: continue
        if s["o"] >= b: break
        pool.fee = s["fee"]
        if s["a0"] < 0: pool.buy(-s["a0"])
        else: pool.sell(-s["a1"])
    pool.fee = fee_near(p, b)
    return pool.sell(tok) / q - 1
def stats(rets, usd):
    rets = [r for r in rets if r is not None]
    if not rets: return "n 0"
    net = [r - GAS_USD / usd for r in rets]
    return (f"n {len(rets):3d} gross mean {statistics.mean(rets):+7.2%} | net mean {statistics.mean(net):+7.2%} median {statistics.median(net):+7.2%}"
            f" win {sum(x > 0 for x in net)/len(net):4.0%} worst {min(net):+7.1%} pulled {sum(r <= -0.999 for r in rets)/len(rets):4.0%}")
# the reaction: lags from the first outside buy of >= 0.0003 ETH to the pull (s12; 64 pools, every one pulled within 193 blocks)
def first_out(p, thr=0.0003):
    for s in p["swaps"]:
        if s["k"] == "other" and s["a0"] < 0 and -s["a0"] >= thr * 1e18: return s
LAGS = sorted(p.get("pull_off", 10**9) - first_out(p)["o"] for p in pools if first_out(p))
def p_pulled(hold): return sum(1 for l in LAGS if l <= hold) / len(LAGS)
RULES = []
for d in (1, 2, 3):
    RULES.append((f"front: buy A+{d}, sell into the fleet's first buy (T+1)", lambda p, d=d: (p["add_off"] + d, p["T"] + 1) if p["T"] else (None, None)))
    for h in (2, 3, 60, 200):
        RULES.append((f"front: buy A+{d}, sell {h} blocks later", lambda p, d=d, h=h: (p["add_off"] + d, p["add_off"] + d + h)))
    RULES.append((f"front: buy A+{d}, sell at L+600", lambda p, d=d: (p["add_off"] + d, 600)))
for k in (0, 1, 2):
    for h in (1, 2, 3, 60):
        if h + k < 2: continue
        RULES.append((f"oracle front: buy at the head of T-{k}, sell at T+{h}", lambda p, k=k, h=h: (p["T"] - k, p["T"] + h) if p["T"] else (None, None)))
for a0 in (115, 121):
    for h in (2, 3, 485 if a0 == 115 else 479):
        RULES.append((f"blind fixed: buy L+{a0}, sell {h} blocks later", lambda p, a0=a0, h=h: (a0, a0 + h)))
RULES.append(("blind fixed: buy A+73, sell 3 blocks later", lambda p: (p["add_off"] + 73, p["add_off"] + 76)))
for e in (1, 2):
    for h in (2, 3, 10, 60, 200):
        RULES.append((f"follow: buy T+{e}, sell {h} blocks later", lambda p, e=e, h=h: (p["T"] + e, p["T"] + e + h) if p["T"] else (None, None)))
def stats(rets, usd):
    rets = [r for r in rets if r is not None]
    if not rets: return "n 0"
    net = [r - GAS_USD / usd for r in rets]
    return (f"n {len(rets):3d} gross {statistics.mean(rets):+7.2%} net {statistics.mean(net):+7.2%} med {statistics.median(net):+7.2%}"
            f" win {sum(x > 0 for x in net)/len(net):4.0%} worst {min(net):+6.1%} pulled {sum(r <= -0.999 for r in rets)/len(rets):4.0%}")
out = {}; table = []
print("reaction lags (blocks from an outside buy >= 0.0003 ETH to the pull), n", len(LAGS), ":", LAGS)
for usd in (5.0, 15.0):
    q = usd / ETH_USD
    print(f"\n===== stake ${usd:.0f} ({q:.6f} ETH) =====")
    for name, f in RULES:
        r0 = []; r4 = []; remp = []
        for p in pools:
            a, b = f(p)
            if a is None: continue
            x = replay(p, a, b, q)
            if x is None: continue
            r0.append(x); r4.append(replay(p, a, b, q, 4))
            pp = p_pulled(b - a); remp.append(x * (1 - pp) + (-1.0) * pp if x > -0.999 else -1.0)
        n0 = statistics.mean(r0) - GAS_USD / usd; n4 = statistics.mean(r4) - GAS_USD / usd; ne = statistics.mean(remp) - GAS_USD / usd
        print(f"{name}\n   no reaction        {stats(r0, usd)}\n   pull 4 after ours  {stats(r4, usd)}\n   empirical lags     n {len(remp)} expected net mean {ne:+7.2%} (P(pulled in hold) {p_pulled(f(pools[5])[1]-f(pools[5])[0]) if f(pools[5])[0] is not None else float('nan'):.0%})")
        table.append(dict(usd=usd, rule=name, n=len(r0), gross0=statistics.mean(r0), net0=n0, net4=n4, net_emp=ne))
        out[f"{usd}|{name}"] = dict(r0=r0, r4=r4, remp=remp)
jdump(dict(lags=LAGS, table=table), "s10_replay.json")
