"""Checks of the simulator (offline, s02_pools.json):
(1) the integer replay of every swap (exact input, fee 100) reproduces every recorded sqrtP of every C-1 pool from its first swap on;
(2) our 5 real fills: our buy re-inserted at its real place (stake = its real ETH) gives the tokens we got on the chain, and the sell at our
    real sell block gives the ETH we got back (the box log's +4.0, +6.7, -0.0, +3.5, -100%);
(3) the pools the engine would arm (launch sqrtP and liquidity equal to the family's) and the liquidity in range over the hold."""
from sim import *
import collections
D = load(); P = D["pools"]
worst = []; nchk = 0; liqchg = collections.Counter()
for p in P:
    sw = p["sw"]
    if not sw: continue
    sp = sw[0]["sqrtP"]
    for a, b in zip(sw, sw[1:]):
        L = b["liq"]
        if L != a["liq"]: liqchg[p["pid"]] += 1
        if L <= 0: sp = b["sqrtP"]; continue
        sp = apply(sp, b)
        e = abs(sp - b["sqrtP"]) / b["sqrtP"]; nchk += 1
        if e > 1e-9: worst.append((e, p["pid"][:12], b["bn"], b["buy"], b.get("cls"))); sp = b["sqrtP"]
print(f"(1) replayed {nchk} swaps step by step: {len(worst)} differ from the chain by more than 1e-9 relative (each then reset to the chain)")
for w in sorted(worst, reverse=True)[:8]: print("    ", w)
print(f"    pools whose in-range liquidity changes between swaps: {len(liqchg)}")
# (1b) the whole path, never reset, from T to T+200, in triggered pools
dev = []
for p in P:
    if p["T"] is None: continue
    sw = p["sw"]; i0 = next(k for k, s in enumerate(sw) if s["off"] >= p["T"]); sp = sw[i0]["sqrtP"]; last = sw[i0]
    for s in sw[i0 + 1:]:
        if s["off"] > p["T"] + 200 or s["liq"] <= 0: break
        sp = apply(sp, s); last = s
    dev.append(abs(sp - last["sqrtP"]) / last["sqrtP"])
print(f"    whole-path replay T..T+200 without resets: max relative error {max(dev):.2e} over {len(dev)} pools")
# (2) our fills
print("(2) our fills, re-simulated (tokens and gross vs the chain):")
for p in sorted(P, key=lambda p: p["ts"]):
    ob = [s for s in p["sw"] if s["cls"] == "ours" and s["buy"]]
    if not ob: continue
    b = ob[0]; os_ = [s for s in p["sw"] if s["cls"] == "ours" and not s["buy"]]
    i = p["sw"].index(b); prev = p["sw"][i - 1]
    t = Trade(p, i - 1, prev["sqrtP"], prev["liq"], b["bn"], b["eth_wei"], skip={x["tx"] for x in ob + os_})
    if os_:
        s = os_[0]; real = s["eth_wei"] / b["eth_wei"] - 1
        # the state our real sell met: every swap before it (its own block included), ours left out
        k = len([x for x in t.later if (x["bn"], x["li"]) < (s["bn"], s["li"])]); _, sp, L, _f = t.path[k]
        sim = v4math.sell_out_int(sp, L, t.tokens, FEE) / b["eth_wei"] - 1
        print(f"    {utc(p['ts'])} {p['pid'][:12]} buy T+{b['off'] - p['T']} tokens sim {t.tokens} chain {b['tok']} (rel {abs(t.tokens - b['tok']) / b['tok']:.1e}); "
              f"sell at buy+{s['bn'] - b['bn']}: chain {real:+.2%} sim {sim:+.2%}; hold-60 rule (lands buy+62, top of block) {t.hold(60)[0]:+.2%} {t.hold(60)[1]}")
    else:
        print(f"    {utc(p['ts'])} {p['pid'][:12]} buy T+{b['off'] - p['T']} tokens sim {t.tokens} chain {b['tok']}; sell reverted (pulled at buy+{p['pullpos'][0] - b['bn']}): hold-60 {t.hold(60)}")
# (3) engine arming
bad = [p for p in P if p["launch_sqrtP"] != SQRTP]
print(f"(3) pools {len(P)}; launch sqrtP != the family's {len(bad)}: " + ", ".join(f"{utc(p['ts'])} {p['pid'][:12]} T {p['T']}" for p in bad))
first_liq = collections.Counter(p["sw"][0]["liq"] == LIQ for p in P if p["sw"])
print(f"    first swap's liquidity == the family's LIQ: {dict(first_liq)}")
