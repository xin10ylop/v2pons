"""Judge 1: my own engine-exact replay of the c1 family (offline; j01_pools.json = the analyst's s02 swaps as data + the pools since 14:14).

What the engine does for a wave family (src/flip_engine.py, read for this; line numbers as of RELEASE 0.9):
  * arming (arm_front): a 2,276-byte value-0 PositionManager multicall, fee 100, ETH pair, no hook; pin true: launch sqrtP and mint
    liquidity must equal the family's (792280926924313289846529216293289 / 100000088127620690885293), else not armed ("new fingerprint").
  * the price copy p["sp"] (float): the launch sqrtP, apply_buy(value) for every router call with flag word 7 == 0 (amount = calldata word 2,
    any size up to max_eth 10) and every ETH-value transaction carrying the token (on_front_buy, wave branch); sells never; fee 100, L = mint L.
  * trigger (on_wave_call): the FIRST router buy of >= min_eth (0.005) sets first_buy; it fires only if its block - launch <= max_blocks
    (and the feed is not stale); a later one never fires. A pull-shaped PositionManager call carrying the token before it makes the pool late.
  * _fire, inside the trigger transaction's processing: min_out = int(buy_out_int(int(copy incl. the trigger), L, stake, 100) * 0.97)
    (BUY_SLIP 0.03); buys later in block T are NOT in it. Our buy lands at the top of T+2 (all 8 real attempts sent on time: 7 at T+2, one at
    T+7) and reverts if the pool gives fewer tokens than min_out.
  * our_buy_landed: feed_tokens = buy_out_int(int(copy), L, stake, 100), then apply_buy(stake) (live).
  * take_profit on every buy the feed shows behind ours (router flag-0 call or ETH-value buy): ret = (sell_out_int(int(copy), L, feed_tokens,
    100) - stake - base_fee * 250,000) / stake >= tp sends the sell in that block.
  * the deadline (ingest, after the block's transactions): the sell is sent when the feed shows our buy's block + hold_blocks (send_after =
    hold_blocks for a front family); it lands 1-2 blocks later (our c1 sells sent at buy+60 landed at +61 once and +62 seven times).
  * _settle: a pull (ModifyLiquidity < 0) landing before our sell (block, index) halts the family (HALTED.front.c1); a pull after it does not
    (the near-miss halt is follow's only). nonbot_halt 0 on the box: no streak halt.

Model here: our buy at the TOP of block T+dB (dB 2; 3 as stress) on the REAL pool (every recorded swap replayed at its own exact input and
fee field, our buy inserted, so it shifts every later price); fill iff tokens >= min_out and no pull at or before that block; the sell sent at
our block + hold (or the take-profit block), landing LAG (2; 1 and 3 as stress) blocks later at the top of that block: sell_out_int on the real
pool after every swap of the earlier blocks; -100% when the pull's block <= the landing block. Gas from our own receipts (skeptic 2's k01, which
I re-derived from k01_receipts.json): filled round trip 4.317e-6 ETH, a fill whose sell met the pull 8.823e-6, a reverted attempt 1.820e-6.
"""
from jc import *
import collections
Q96 = 1 << 96; FEE = 100; SLIP = 0.03; MIN_TRIG = 5 * 10 ** 15; MAX_ETH = 10 * 10 ** 18; GAS_RT_COPY = 20_000_000 * 250_000
ETHUSD = 2500.0
GAS = json.load(open(SH("skeptic2/k01_gas.json")))
G_FILL, G_PULLED, G_REV = GAS["per_fill_wei"], GAS["per_pulled_wei"], GAS["per_revert_wei"]
RIN = {}
for fn in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl"), JD("j00_txs.jsonl")):
    for l in open(fn):
        t = json.loads(l)
        if t["to"] == ROUTER: RIN[t["hash"]] = t["input"]
wd = lambda inp, i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)

def netx(x, fee): return x - (x * fee + 999_999) // 1_000_000
def sp_swap(sp, L, s):
    if s["buy"]:
        x = netx(s["eth_wei"], s["fee"]); den = L + (x * sp) // Q96; return (L * sp + den - 1) // den
    return sp + (netx(s["tok"], s["fee"]) * Q96) // L
def sp_buy(sp, L, eth, fee):
    x = netx(eth, fee); den = L + (x * sp) // Q96; return (L * sp + den - 1) // den

def seen(s):
    """the amount the engine's copy applies for this swap's transaction, or None (not a buy the feed shows as one)"""
    if not s["buy"] or s["cls"] == "ours": return None
    if s["cls"] == "router":
        inp = RIN.get(s["tx"])
        if inp is not None:
            if wd(inp, 7) != 0: return None                 # the router's other action
            a = wd(inp, 2)
        else: a = s["eth_wei"]
        return a if a <= MAX_ETH else None
    v = s.get("value") or 0
    return v if v > 0 else None

def engine_T(p, max_blocks):
    """(index of the trigger swap, its offset) or (None, why)"""
    for k, s in enumerate(p["sw"]):
        if s["cls"] == "router" and s["buy"]:
            a = seen(s)
            if a is not None and a >= MIN_TRIG:
                if s["off"] > max_blocks: return None, f"first trigger-size router buy at +{s['off']} > max_blocks"
                if p["pullpos"] and tuple(p["pullpos"]) < (s["bn"], s["li"]): return None, "pulled before the trigger"
                return k, s["off"]
    return None, "no router buy >= 0.005 ETH"

def simulate(p, stake, max_blocks, exits, dB=2, lag=2, check_minout=True):
    """one engine attempt on pool p. Returns dict: fill, why, T, and per exit (gross, pulled, send_off, land_off)"""
    sw = [s for s in p["sw"] if s["cls"] != "ours"]
    q = dict(p, sw=sw)
    k0, T = engine_T(q, max_blocks)
    if k0 is None: return {"fill": False, "attempt": False, "why": T}
    L0 = p["mint_liq"]; Tb = sw[k0]["bn"]; B = Tb + dB
    pullb = p["pullpos"][0] if p["pullpos"] else None
    copy = float(p["launch_sqrtP"])
    for s in sw[:k0 + 1]:
        a = seen(s)
        if a is not None: copy = v4math.sqrt_after_buy(copy, L0, netx(a, FEE))
    min_out = int(v4math.buy_out_int(int(copy), L0, stake, FEE) * (1 - SLIP))
    base = {"attempt": True, "T": T, "Tb": Tb, "B": B, "pull_after_buy": None if pullb is None else pullb - B, "min_out": min_out}
    if pullb is not None and pullb <= B: return dict(base, fill=False, why="pulled at or before our buy's block")
    sp = L = fee = None; i_ins = 0; copy_at = copy
    sp, L, fee = p["launch_sqrtP"], L0, FEE
    for k, s in enumerate(sw):
        if s["bn"] < B:
            if s["liq"] > 0: sp, L, fee = s["sqrtP"], s["liq"], s["fee"]
            i_ins = k + 1
            if k > k0:
                a = seen(s)
                if a is not None: copy_at = v4math.sqrt_after_buy(copy_at, L0, netx(a, FEE))
        else: break
    tokens = v4math.buy_out_int(sp, L, stake, fee)
    short = tokens / (min_out / (1 - SLIP)) - 1
    if check_minout and tokens < min_out: return dict(base, fill=False, why="minOut", short=short)
    feed_tokens = v4math.buy_out_int(int(copy_at), L0, stake, FEE)
    c = v4math.sqrt_after_buy(copy_at, L0, netx(stake, FEE))
    sp = sp_buy(sp, L, stake, fee); path = []; tpev = []
    st0 = (sp, L, fee)
    maxoff = max(e[1] for e in exits) + 6
    for s in sw[i_ins:]:
        if s["bn"] > B + maxoff: break
        if s["liq"] > 0: sp = sp_swap(sp, s["liq"], s); path.append((s["bn"], sp, s["liq"], s["fee"]))
        a = seen(s)
        if a is not None:
            c = v4math.sqrt_after_buy(c, L0, netx(a, FEE))
            tpev.append((s["bn"], (v4math.sell_out_int(int(c), L0, feed_tokens, FEE) - stake - GAS_RT_COPY) / stake))
    def at(X):
        st = st0
        for x in path:
            if x[0] < X: st = x[1:]
            else: break
        return st
    def ret_landing(X):
        if pullb is not None and pullb <= X: return -1.0, True
        s_, L_, f_ = at(X)
        return v4math.sell_out_int(s_, L_, tokens, f_) / stake - 1, False
    res = {}
    for e in exits:
        kind, n, tp = e
        send = B + n
        if kind == "tp":
            for bn, r in tpev:
                if bn > B + n: break
                if pullb is not None and bn > pullb: break
                if r >= tp: send = bn; break
        g, pulled = ret_landing(send + lag)
        res[ename(e)] = (g, pulled, send - B, send + lag - B)
    return dict(base, fill=True, why="fill", short=short, res=res)

def ename(e): return f"hold {e[1]}" if e[0] == "hold" else f"tp {round(e[2] * 100)}% cap {e[1]}"
HOLDS = [10, 15, 20, 25, 30, 35, 40, 60]
EXITS = [("hold", n, None) for n in HOLDS] + [("tp", c, tp) for c in (30, 40) for tp in (0.04, 0.06)]

def usd(r, ex, stake):
    """$ of one attempt (reverts cost gas only) at ETHUSD"""
    if not r.get("attempt"): return None
    if not r["fill"]: return -G_REV / 1e18 * ETHUSD
    g, pulled = r["res"][ex][0], r["res"][ex][1]
    return (g * stake - (G_PULLED if pulled else G_FILL)) / 1e18 * ETHUSD

# ------------------------------------------------------------------ regimes (with the engine's own T)
OUT = ("recurring", "oneoff"); BD = "0xbd9dc5f684ed24f4a06559ff9dc736748cbbbc41"
import calendar
T1315 = calendar.timegm((2026, 10, 12, 13, 15, 0))
def regime(p, T):
    """ours / holder-early (outside >= 0.001 ETH bought by T+5, incl. before T, still held at min(T+62, pull)) / holder-later / bd13 / sold / none"""
    if any(s["cls"] == "ours" and s["buy"] for s in p["sw"]): return "ours"
    end = min(T + 62, p["pull"] if p["pull"] is not None else 1 << 40); hs, sold = [], []
    for s in p["sw"]:
        if not (s["buy"] and s["cls"] in OUT and s["eth"] >= 0.001 and s["off"] <= T + 62): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        sl = any((not x["buy"]) and x.get("from") == s.get("from") and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end for x in p["sw"])
        (sold if sl else hs).append(s)
    bd = p["ts"] >= T1315 and any(s["buy"] and s.get("from") == BD and s["eth"] >= 0.001 and (not p["pullpos"] or (s["bn"], s["li"]) < tuple(p["pullpos"])) for s in p["sw"])
    if hs: return ("holder-pre" if hs[0]["off"] < T else "holder-early" if hs[0]["off"] - T <= 5 else "holder-later")
    if bd: return "bd13"
    if sold: return "sold"
    return "none"

def run(pools, stake, max_blocks, dB=2, lag=2, check=True, exits=EXITS):
    rows = []
    for p in pools:
        r = simulate(p, stake, max_blocks, exits, dB, lag, check)
        if not r.get("attempt"): continue
        r["pid"] = p["pid"]; r["ts"] = p["ts"]; r["reg"] = regime(p, r["T"]); r["shape"] = p["shape"]; r["new"] = p.get("new", False)
        rows.append(r)
    return rows

def boot(vals, n=10000, seed=1):
    import random
    rnd = random.Random(seed); m = len(vals)
    if m == 0: return (None, None)
    ms = sorted(sum(vals[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n) - 1]

def load_pools(head_margin=True):
    D = json.load(open(JD("j01_pools.json"))); head = D["head"]
    out = []
    for p in D["pools"]:
        if p["shape"] == "other" or not p["sw"]: continue
        if head_margin and head - p["lb"] < 400 + 100: p["young"] = True
        out.append(p)
    return out, head

if __name__ == "__main__":
    pools, head = load_pools()
    stake = 2 * 10 ** 15
    # validation: our 8 real attempts
    ours_rev = {"0x35869115", "0xd4654e14", "0x266d00f1"}
    real = {"0x5ec68315": (+0.0402, 61), "0xd6180333": (+0.0666, 62), "0x6d80b816": (-0.0001, 62), "0x0e4cc1d8": (+0.0346, 62), "0xb47b706f": (-1.0, 62)}
    print("(1) our 8 real attempts under my model (0.002 ETH, max_blocks 400, buy at the top of T+2):")
    for p in sorted(pools, key=lambda p: p["ts"]):
        if p["pid"][:10] in real or p["pid"][:10] in ours_rev:
            r = simulate(p, stake, 400, [("hold", 59, None), ("hold", 60, None)], 2, 2)
            r1 = simulate(p, stake, 400, [("hold", 59, None), ("hold", 60, None)], 2, 1)
            if r["fill"]:
                rr, land = real[p["pid"][:10]]
                g = r1["res"]["hold 60"][0] if land == 61 else r["res"]["hold 60"][0]
                print(f"   {utc(p['ts'])} {p['pid'][:10]} real FILL {rr:+.2%} (sell landed buy+{land}); model FILL, tokens/min_out-1 {r['short'] + 0.03:+.2%} over the quote; sell at buy+{land} {g:+.2%}; T +{r['T']}")
            else:
                print(f"   {utc(p['ts'])} {p['pid'][:10]} real REVERT; model {r['why']} (tokens vs the copy's quote {r.get('short', 0):+.2%}, the limit is -3%); T +{r['T']}")
    # the 0xcf1d880b case
    p = next(p for p in pools if p["pid"].startswith("0xcf1d880b"))
    r = simulate(p, stake, 400, EXITS, 2, 2)
    tb = [(s["off"], s["bn"], round(s["eth"], 4), s["cls"]) for s in p["sw"] if s["buy"] and s["cls"] in ("router", "recurring", "oneoff") and s["off"] <= r["T"] + 25]
    print(f"\n(2) 0xcf1d880b: T +{r['T']}, model {r['why']} (tokens vs quote {r.get('short', 0):+.2%}); pull +{p['pull']} = our buy + {r['pull_after_buy']}; buys to T+25: {tb}")
    r3 = simulate(p, stake, 400, EXITS, 2, 2, check_minout=False)
    print(f"    without minOut it would fill and: " + ", ".join(f"{k} {v[0]:+.1%}" for k, v in r3["res"].items()))
