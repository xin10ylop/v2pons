"""Every schedule rule as a firing rule, trained on the older 2/3 of the 3.0/5.0 pools and measured on the most recent 1/3 (held out).
A rule gives, per pool, the block D after which we decide (using only blocks <= D) and our landing block B = D + delta (delta 1 or 2,
the engine lands 1-2 blocks after it decides). Outcomes, with the operator's reaction modelled from this window's 27 pre-T outside buys
(a05: pull lag r after the buy 3:6 4:6 5:4 6:4 7:2 9:1 17:2 18:1 23:1; the bot never bought after one):
 - T <= D: no fire (the engine sees the bot's buy first).
 - D < T < B: late, our buy lands behind the bot's: we sell at B+1 (replayed exactly).
 - T >= B: a front; it survives with probability P(r > T + s - B) (our sell lands at T + s, s = 1 conservative / 0 optimistic) and then
   earns the exact replay (buy q at the head of B, the bot's buy at T, our sell at the head of T + 1); otherwise -100%.
q = 0.0058 ETH ($15 at 2,570), fee 1% each way, gas $0.02 a leg."""
import pickle, json, collections, bisect, sys, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; acts = D["acts"]
USD = 2570.0; GAS = 0.04; Q = int(0.0058e18)
R = collections.Counter({3: 6, 4: 6, 5: 4, 6: 4, 7: 2, 9: 1, 17: 2, 18: 1, 23: 1}); NR = sum(R.values())
def p_survive(k):   # P(r > k)
    return sum(v for r, v in R.items() if r > k) / NR
Q96 = 1 << 96
def net(x, fee): return x - (x * fee + 999_999) // 1_000_000
def buy_sp(sp, L, x, fee):
    x = net(x, fee); num = L * sp; den = L + (x * sp) // Q96; return (num + den - 1) // den
def pool_state(p):
    adds = [m for m in p["ml"] if m["dL"] > 0 and m["off"] == 0]
    return p["sp0"], sum(m["dL"] for m in adds)
def front_ret(p, B, sell_at):
    """our buy q at the head of block B, every swap in [B, sell_at) re-applied by amount, our sell at the head of sell_at"""
    sp, L = pool_state(p); fee = p["fee"]
    for s in p["sw"]:
        if s["bn"] < B and s["buy"]: sp = buy_sp(sp, L, int(s["q"] * 1e18), fee)
    tok = v4math.buy_out_int(sp, L, Q, fee); sp = buy_sp(sp, L, Q, fee)
    for s in p["sw"]:
        if B <= s["bn"] < sell_at:
            if s["buy"]: sp = buy_sp(sp, L, int(s["q"] * 1e18), fee)
            else: sp = sp + (net(s["t"], fee) * Q96) // L
    eth = v4math.sell_out_int(sp, L, tok, fee)
    return (eth - Q) / Q - GAS / (Q / 1e18 * USD)
def outcome(p, Dd, delta, s):
    T = p["Tbn"]; B = Dd + delta
    if T <= Dd: return None
    if T < B: return ("late", front_ret(p, B, B + 1))
    ps = p_survive(T + s - B)
    win = front_ret(p, B, T + 1)
    return ("front", ps * win + (1 - ps) * (-1.0 - GAS / (Q / 1e18 * USD)), T - B, ps, win)
P = sorted([p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None], key=lambda p: p["L"])
cut = len(P) * 2 // 3; train, test = P[:cut], P[cut:]
print(f"3.0/5.0 pools with T: {len(P)}; train {len(train)} (L {train[0]['L']}..{train[-1]['L']}), test {len(test)} (L {test[0]['L']}..{test[-1]['L']})")
def evaluate(rows):
    fired = [r for r in rows if r is not None]
    if not fired: return {"fires": 0}
    fr = [r for r in fired if r[0] == "front"]
    lead = collections.Counter(min(r[2], 9) for r in fr)
    hit01 = sum(1 for r in fr if r[2] <= 1); hit2 = sum(1 for r in fr if r[2] <= 2)
    ev = st.mean(r[1] for r in fired)
    return {"fires": len(fired), "late": len(fired) - len(fr), "T-B in {0,1}": hit01, "T-B<=2": hit2, "hit01%": round(100 * hit01 / len(fired), 1),
            "EV%/fire": round(100 * ev, 1), "lead(T-B) hist": dict(sorted(lead.items()))}
# --- rule family 1: constant decision offset d (the hazard rule)
print("\n== R1 constant: decide at L+d if no bot buy yet; land at L+d+delta")
best = {}
for delta in (1, 2):
    for s in (1, 0):
        res = []
        for d in range(15, 62):
            e = evaluate([outcome(p, p["L"] + d, delta, s) for p in train])
            if e["fires"] >= 5: res.append((e["EV%/fire"], d, e))
        res.sort(key=lambda x: -x[0]); best[(delta, s)] = res[0][1]
        print(f" delta {delta} sell+{s}: train best d {res[0][1]}: {res[0][2]}")
        print(f"     held-out at that d: {evaluate([outcome(p, p['L'] + res[0][1], delta, s) for p in test])}")
for d in (25, 30, 35, 40, 45, 50, 53, 55, 57):
    print(f"  all pools d {d} delta 1 sell+1: {evaluate([outcome(p, p['L'] + d, 1, 1) for p in P])}")
# --- rule family 2: queue / global cadence: decide at the first bot action in another pool at or after L+a, land delta later
print("\n== R2 queue: fire on the first bot action in another pool at block >= L+a (land delta after it)")
ab = sorted((a["bn"], a["token"]) for a in acts)
abn = [x[0] for x in ab]
def first_other(p, a):
    i = bisect.bisect_left(abn, p["L"] + a)
    while i < len(ab) and ab[i][1] == p["token"]: i += 1
    return ab[i][0] if i < len(ab) else None
for delta in (1, 2):
    res = []
    for a in range(15, 60):
        e = evaluate([outcome(p, first_other(p, a), delta, 1) for p in train])
        if e["fires"] >= 5: res.append((e["EV%/fire"], a, e))
    res.sort(key=lambda x: -x[0])
    print(f" delta {delta}: train best a {res[0][1]}: {res[0][2]}")
    print(f"     held-out: {evaluate([outcome(p, first_other(p, res[0][1]), delta, 1) for p in test])}")
# --- rule family 3: pair: for the second pool of a pair, decide at L2 + (T1 - L1) + k  (k chosen on train)
print("\n== R3 pair: second launch of a pair (<= 120 blocks), decide at L2 + (T1 - L1) + k, only if T1 is already known")
def pairs(PP):
    out = []
    for a, b in zip(PP, PP[1:]):
        if b["L"] - a["L"] <= 120: out.append((a, b))
    return out
for delta in (1,):
    res = []
    for k in range(-20, 21):
        rows = [outcome(b, b["L"] + a["T"] + k, delta, 1) if a["Tbn"] < b["L"] + a["T"] + k - 1 else None for a, b in pairs(train)]
        e = evaluate(rows)
        if e["fires"] >= 5: res.append((e["EV%/fire"], k, e))
    res.sort(key=lambda x: -x[0])
    print(f" train best k {res[0][1]}: {res[0][2]}")
    k = res[0][1]
    print(f"     held-out: {evaluate([outcome(b, b['L'] + a['T'] + k, 1, 1) if a['Tbn'] < b['L'] + a['T'] + k - 1 else None for a, b in pairs(test)])}")
# --- the oracle: a perfect predictor (land at T-1) and a +-1 predictor, to show what a rule would earn if it existed
print("\n== oracle (not a rule): land exactly at T-1 / at T-2 / at T (head) ; the front's exact replay")
for lead in (0, 1, 2):
    rows = [outcome(p, p["Tbn"] - lead - 1, 1, 1) for p in test]
    print(f"  land at T-{lead}: {evaluate(rows)}; win p50 {round(100 * st.median(r[4] for r in rows if r and r[0] == 'front'), 2)}%")
