#!/usr/bin/env python3
"""Exit timing against a faster operator: Oct 8's original-launcher launches (follow entry, flip_engine 0.8), priced by the verified
follow pricer (protect/follow.py = yday/follow.py with the cache read only), under several exit rules, with the operator's reaction
modelled as a pull at OUR buy block + lag (lag 2..6) on top of the chain's own pull, and on the paper (the chain's pull only).

Conventions are follow.py's: our buy lands at trigger+1 or trigger+2, last in its block; tokens = the chain after every other swap of
that block; minOut = the engine's feed copy through the trigger tx x 0.97 (under it: buy_reverted, -gas); a sell lands send+1 (fast;
every live sell of the current exit landed buy+3 after being sent at buy+2) or send+2 (slow) and is priced at the head of its landing
block (the chain after the block before + our buy, 1/sqrtP additive; an earlier sell of ours in the same trade adds to sqrtP).
A pull at or before a sell's landing block takes that sell's tokens (-their stake share, plus the pulled sell's gas). The TP check is
the engine's: on the feed copy (receipt liquidity, every feed buy's value), after base_fee x 250k gas, on every feed buy >= 0.0002 ETH
behind ours.

    python3 exits_bt.py     -> exits_bt.json, printed tables
"""
import sys, os, json, statistics as st, collections, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import follow as F
from follow import v4math, s128, net_of_fee, pool_from_receipt, Q96

STAKES = (0.0012, 0.1)
LAGS = (2, 3, 4, 5, 6)
TLAGS = (3, 4, 5, 6, 7)              # second reaction model: the pull at the TRIGGER block + lag (a reaction to an outsider's trigger)
LANDS = (1, 2, 3)
OUTLIER = 83090333                   # 06:05 launch: a 0.19 ETH buy at T+4 makes +40% for any exit landing after it (0.9 points of a 46-launch mean)
TP = 0.01


# ------------------------------------------------------------------ per launch, as follow.price_launch up to the fire
def prep(p, L, ours_hashes):
    b0 = p["block"]; rec = L["rec"]; blocks = L["blocks"]
    bt = {int(b["number"], 16): b for b in blocks}
    base_fee = {n: int(b["baseFeePerGas"], 16) for n, b in bt.items()}
    pool = pool_from_receipt(rec) if rec and rec.get("status") == "0x1" else None
    if pool is None or pool["pid"] != p["pid"]:
        return None, "no pool"
    fee = pool["fee"]; liq = pool["liq"]; token = pool["token"].lower(); tb = bytes.fromhex(token)
    eligible = pool["c0"] == "0" * 40 and pool["hooks"] == "0" * 40 and F.FEE_MIN_PPM <= fee <= F.FEE_MAX_PPM and liq >= F.MIN_LIQUIDITY
    ls = sorted(L["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    swaps = []; mls = []
    for l in ls:
        bn = int(l["blockNumber"], 16); d = l["data"]
        if l["topics"][0] == F.T_SWAP:
            x = {"bn": bn, "a0": s128(F.W(d, 0)), "sp": F.W(d, 2), "L": F.W(d, 3), "tx": l["transactionHash"], "sender": l["topics"][2][-40:]}
            if not (x["sender"] == F.RELAY or l["transactionHash"] in ours_hashes):
                swaps.append(x)
        elif l["topics"][0] == F.T_ML:
            mls.append({"bn": bn, "lo": F.sgn(F.W(d, 0)), "hi": F.sgn(F.W(d, 1)), "dl": F.sgn(F.W(d, 2))})
    pulls = [m for m in mls if m["dl"] < 0]
    pull = pulls[0]["bn"] if pulls else None
    feed = []
    for k in range(F.SCAN):
        b = bt.get(b0 + k)
        if b is None:
            continue
        for t in b["transactions"]:
            to = (t.get("to") or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); value = int(t["value"], 16)
            if to in F.LAUNCHERS or (F.LAUNCH_SELECTORS and data[:4].hex() in F.LAUNCH_SELECTORS):
                continue
            if value == 0 or len(data) < 20:
                continue
            if tb in data and to != token:
                feed.append({"bn": b0 + k, "idx": int(t["transactionIndex"], 16), "value": value, "from": t["from"][2:].lower()})
    feed = [f for f in feed if f["from"] != F.WALLET]
    trig = next((f for f in feed if f["value"] >= F.MIN_TRIGGER_WEI), None)
    if trig is None:
        return None, "no trigger"
    T = trig["bn"]; off = T - b0
    if off > F.TRIGGER_MAX_BLOCKS:
        return None, "late (> TRIGGER_MAX_BLOCKS)"
    if off <= F.ARM_LAG:
        return None, "late (before arming)"
    if not eligible:
        return None, "not eligible"
    sp_feed_trig = float(pool["sqrt_p"])
    for f in feed:
        if (f["bn"], f["idx"]) > (trig["bn"], trig["idx"]):
            break
        sp_feed_trig = v4math.sqrt_after_buy(sp_feed_trig, liq, net_of_fee(f["value"], fee))

    def chain_after(bn):
        prev = [x for x in swaps if x["bn"] <= bn]
        return (prev[-1]["sp"], prev[-1]["L"]) if prev else (pool["sqrt_p"], liq)
    pos = [m["lo"] for m in mls if m["dl"] > 0 and m["lo"] < pool["tick0"] <= m["hi"]]
    sqrt_lo = (1.0001 ** (max(pos) / 2)) * Q96 if pos else 0.0
    return {"p": p, "b0": b0, "fee": fee, "liq": liq, "pool": pool, "swaps": swaps, "pull": pull, "feed": feed, "T": T, "off": off,
            "sp_feed_trig": sp_feed_trig, "base_fee": base_fee, "chain_after": chain_after, "sqrt_lo": sqrt_lo}, None


def position(c, stake, land):
    """our buy at T+land: the tokens (chain), minOut, the engine's feed copy after our buy"""
    X = int(round(stake * 1e18)); fee = c["fee"]; liq = c["liq"]; xn = net_of_fee(X, fee)
    expected = v4math.buy_out_int(int(c["sp_feed_trig"]), liq, X, fee); min_out = int(expected * (1 - F.BUY_SLIP))
    B = c["T"] + land
    spB, LB = c["chain_after"](B)
    tokens = v4math.buy_out_int(spB, LB, X, fee) if LB > 0 else 0
    sp_f = float(c["pool"]["sqrt_p"])
    for f in c["feed"]:
        if f["bn"] > B:
            break
        sp_f = v4math.sqrt_after_buy(sp_f, liq, net_of_fee(f["value"], fee))
    feed_tokens = v4math.buy_out_int(int(sp_f), liq, X, fee)
    sp_f = v4math.sqrt_after_buy(sp_f, liq, xn)
    crossed_at_buy = (LB != liq) or (Q96 / (Q96 / spB + xn / LB) <= c["sqrt_lo"])
    return {"X": X, "xn": xn, "B": B, "spB": spB, "LB": LB, "tokens": tokens, "min_out": min_out, "feed_tokens": feed_tokens, "sp_f": sp_f,
            "crossed_at_buy": crossed_at_buy}


def tp_scan(c, q, thresholds, presold=()):
    """the engine's take-profit on its feed copy: the first feed buy >= MIN_TRIGGER behind ours, in a block B+k with k in
    `thresholds`, at which the trade (what an earlier partial sell of ours fetched on the feed copy + the rest sold now) prices at
    >= thresholds[k] after base_fee x 250k (x 350k with a split's third tx). presold: [(land_block, frac)] already sent, on the copy
    at the head of their landing block. Returns (block, r) or (None, None); also every check made."""
    liq = c["liq"]; fee = c["fee"]; X = q["X"]; B = q["B"]; sp = q["sp_f"]
    pending = sorted(presold); got = 0; held = q["feed_tokens"]; gas_units = 350_000 if presold else 250_000
    last = max(thresholds) if thresholds else 0
    checks = []
    for f in c["feed"]:
        if f["bn"] <= B:
            continue
        if f["bn"] > B + last:
            break
        while pending and pending[0][0] <= f["bn"]:
            lb, fr = pending.pop(0); qq = int(q["feed_tokens"] * fr)
            got += v4math.sell_out_int(int(sp), liq, qq, fee); held -= qq
            sp = sp + (net_of_fee(qq, fee) * Q96) / liq
        sp = v4math.sqrt_after_buy(sp, liq, net_of_fee(f["value"], fee))
        if f["value"] < F.MIN_TRIGGER_WEI:
            continue
        k = f["bn"] - B
        if k not in thresholds:
            continue
        eth = got + v4math.sell_out_int(int(sp), liq, held, fee)
        r = (eth - X - c["base_fee"].get(f["bn"], 21_000_000) * gas_units) / X
        checks.append((k, round(r, 5)))
        if r >= thresholds[k]:
            return f["bn"], r, checks
    return None, None, checks


def feed_buys_in(c, q, k):
    return [f for f in c["feed"] if f["bn"] == q["B"] + k and f["value"] >= F.MIN_TRIGGER_WEI]


# ------------------------------------------------------------------ exit rules: [(send_block, fraction, why)]
def plan_V0(c, q, dl=1):
    bn, r, ch = tp_scan(c, q, {1: TP, 2: TP})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 2, 1.0, "deadline")]


def plan_V1(c, q, dl=1):
    bn, r, ch = tp_scan(c, q, {1: TP})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 1, 1.0, "deadline")]


def plan_V2(c, q, dl=1, frac=0.5):
    """half sent at B+1 (whatever it prices at); the other half by the V0 rule on the whole trade"""
    first = (q["B"] + 1, frac, "split")
    bn, r, ch = tp_scan(c, q, {1: TP, 2: TP}, presold=[(q["B"] + 1 + dl, frac)])
    second = (bn, 1 - frac, "tp") if bn else (q["B"] + 2, 1 - frac, "deadline")
    return [first, second]


def plan_V3(c, q, dl=1):
    bn, r, ch = tp_scan(c, q, {1: TP, 2: 0.003})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 2, 1.0, "deadline")]


def plan_V4a(c, q, dl=1):
    """quiet-out: at B+1, sell if a buy prices the trade at TP, or if B+1 brought no real buy at all (the crowd is not coming, the
    extra block is only the pull's risk); hold to B+2 (TP / deadline) only when a crowd buy came at B+1 but fell short of TP"""
    bn, r, ch = tp_scan(c, q, {1: TP})
    if bn:
        return [(bn, 1.0, "tp")]
    if not feed_buys_in(c, q, 1):
        return [(q["B"] + 1, 1.0, "quiet")]
    bn, r, ch = tp_scan(c, q, {2: TP})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 2, 1.0, "deadline")]


def plan_V4b(c, q, dl=1):
    """take any profit at B+1 (threshold 0 after gas), else the V0 rule at B+2"""
    bn, r, ch = tp_scan(c, q, {1: 0.0, 2: TP})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 2, 1.0, "deadline")]


def plan_V4c(c, q, dl=1):
    """V4a + V4b: at B+1 sell on any profit or on no buy; hold to B+2 only when a B+1 buy left the trade under water"""
    bn, r, ch = tp_scan(c, q, {1: 0.0})
    if bn:
        return [(bn, 1.0, "tp")]
    if not feed_buys_in(c, q, 1):
        return [(q["B"] + 1, 1.0, "quiet")]
    bn, r, ch = tp_scan(c, q, {2: TP})
    return [(bn, 1.0, "tp")] if bn else [(q["B"] + 2, 1.0, "deadline")]


def plan_V4d(c, q, dl=1):
    """deadline anchored on the trigger, not on our buy: the crowd's next buy comes at T+2/T+3 whatever block our buy landed in, so
    the deadline sell goes when the feed shows T+3 (lands T+4), never before B+1; TP 1% on every block up to it"""
    d = max(q["B"] + 1, c["T"] + 3)
    bn, r, ch = tp_scan(c, q, {k: TP for k in range(1, d - q["B"] + 1)})
    return [(bn, 1.0, "tp")] if bn else [(d, 1.0, "deadline")]


def plan_fixed(k):
    def f(c, q, dl=1):
        return [(q["B"] + k, 1.0, f"fixed+{k}")]
    return f


VARIANTS = {"V0 current": plan_V0, "V1 deadline B+1": plan_V1, "V2 split 1/2 at B+1": plan_V2, "V3 TP 1%/0.3%": plan_V3,
            "V4d deadline at T+3": plan_V4d, "V4a quiet-out": plan_V4a, "V4b TP 0% at B+1": plan_V4b, "V4c quiet-out + TP 0%": plan_V4c,
            "ref sell sent B+0 (lands B+1)": plan_fixed(0), "ref sell sent B+3 (lands B+4)": plan_fixed(3)}


# ------------------------------------------------------------------ pricing a plan
def price(c, q, plan, G, dl=1, pull_at=None):
    """plan's sells landing send+dl; pull_at: the block the liquidity goes (None: never). Returns a record."""
    X = q["X"]; fee = c["fee"]; B = q["B"]; bf = c["base_fee"]
    sells = sorted([(s + dl, fr, why) for s, fr, why in plan], key=lambda x: x[0])
    bf_b = bf.get(B, 21_000_000)
    why_final = sells[-1][2]
    if (c["pull"] is not None and c["pull"] < B) or (pull_at is not None and pull_at != c["pull"] and pull_at <= B):
        # the chain's pull before our buy block (follow.py), or a modelled reaction at/before it (our buy is last in its block: it
        # meets an empty pool, its minOut fails): the buy reverts, both txs' gas
        gas = G["buy_gas"] * bf_b + G["sell_gas"] * bf_b * len(sells)
        return {"exit": "pull_before_buy", "ret": -gas / X, "why": why_final, "lands": [s - B for s, _, _ in sells], "caught": 0}
    if q["tokens"] < q["min_out"]:
        gas = G["buy_gas"] * bf_b + sum(G["sell_gas"] * bf.get(S, 21_000_000) for S, _, _ in sells)
        return {"exit": "buy_reverted", "ret": -gas / X, "why": why_final, "lands": [s - B for s, _, _ in sells], "caught": 0}
    eth = 0; gas = G["buy_gas"] * bf_b; caught = 0; done = []; parts = []; crossed = False
    left = q["tokens"]
    for i, (S, fr, why) in enumerate(sells):
        qq = left if i == len(sells) - 1 else int(q["tokens"] * fr)
        left -= qq
        bf_s = bf.get(S, 21_000_000)
        if pull_at is not None and pull_at <= S:
            caught += 1; gas += G["sell_gas_pulled"] * bf_s; parts.append(("pulled", fr)); continue
        spc, Lc = c["chain_after"](S - 1)
        s = Q96 / (Q96 / spc + q["xn"] / Lc)                                  # our buy in (1/sqrtP adds)
        for qd in done:                                                      # our earlier sells in (sqrtP adds)
            s = s + net_of_fee(qd, fee) * Q96 / Lc
        e = v4math.sell_out_int(int(s), Lc, qq, fee)
        eth += e; gas += G["sell_gas"] * bf_s; done.append(qq); parts.append((round((e - X * fr) / (X * fr), 5), fr))
        if Lc != q["LB"] or Lc != c["liq"] or s <= c["sqrt_lo"]:
            crossed = True
    ret = (eth - X - gas) / X
    ex = "pull_first" if caught == len(sells) else ("partly_pulled" if caught else why_final)
    return {"exit": ex, "ret": ret, "why": why_final, "lands": [s - B for s, _, _ in sells], "caught": caught, "parts": parts,
            "crossed": crossed or q["crossed_at_buy"]}


def main():
    data = F.gather()
    G = F.measure_gas(data)
    ctxs = []; skips = collections.Counter()
    for p in data["orig"]:
        L = data["launch"][p["pid"]]
        ours = {t["hash"] for b in L["blocks"] for t in b["transactions"] if t["from"][2:].lower() == F.WALLET}
        c, why = prep(p, L, ours)
        if c is None:
            skips[why] += 1; continue
        ctxs.append(c)
    print(f"gas: buy {G['buy_gas']} sell {G['sell_gas']} pulled sell {G['sell_gas_pulled']}; {len(data['orig'])} orig launches, traded {len(ctxs)}, skips {dict(skips)}")

    # validation against follow.json / follow_stakes.json (V0, paper)
    ref = {0.0012: json.load(open(os.path.join(F.SCRATCH, "yday", "follow.json"))), 0.1: json.load(open(os.path.join(F.SCRATCH, "yday", "follow_stakes.json")))}
    worst = 0.0; nchk = 0
    for stake in STAKES:
        R = {r["block"]: r for r in ref[stake]["launches"] if r["results"]}
        for c in ctxs:
            for land in (1, 2):
                q = position(c, stake, land)
                for dl, sp in ((1, "fast"), (2, "slow")):
                    mine = price(c, q, plan_V0(c, q, dl), G, dl=dl, pull_at=c["pull"])
                    theirs = R[c["b0"]]["results"][str(stake)][f"land{land}_{sp}"]
                    worst = max(worst, abs(mine["ret"] - theirs["ret"])); nchk += 1
                    if abs(mine["ret"] - theirs["ret"]) > 1e-5 or (mine["exit"] != theirs["exit"] and not (mine["exit"] == "tp" and theirs["exit"] == "take_profit")):
                        print("MISMATCH", stake, c["b0"], land, sp, mine["exit"], mine["ret"], theirs["exit"], theirs["ret"])
    print(f"validation V0 paper vs follow.json/follow_stakes.json: {nchk} trade prices, max |ret diff| {worst:.2e}")

    out = {"meta": {"stakes": STAKES, "lags": LAGS, "n_launches": len(ctxs), "gas": {k: v for k, v in G.items() if k not in ("buys", "sells", "sells_pulled")},
                    "validation_max_abs_ret_diff_vs_follow_json": worst},
           "summary": {}, "per_launch": []}
    per = collections.defaultdict(dict)
    for stake in STAKES:
        for land in LANDS:
            for dl in (1, 2):
                for name, plan in VARIANTS.items():
                    rows = []
                    for c in ctxs:
                        q = position(c, stake, land)
                        pl = plan(c, q, dl)
                        rec = {"paper": price(c, q, pl, G, dl=dl, pull_at=c["pull"])}
                        for lag in LAGS:
                            pa = q["B"] + lag if c["pull"] is None else min(c["pull"], q["B"] + lag)
                            rec[lag] = price(c, q, pl, G, dl=dl, pull_at=pa)
                        for lag in TLAGS:
                            pa = c["T"] + lag if c["pull"] is None else min(c["pull"], c["T"] + lag)
                            rec[f"T{lag}"] = price(c, q, pl, G, dl=dl, pull_at=pa)
                        rec["b0"] = c["b0"]
                        rows.append(rec)
                        per[(c["b0"], stake, land, dl)][name] = {"sends": [(s - q["B"], fr, w) for s, fr, w in pl], "paper": rec["paper"]["ret"], "exit": rec["paper"]["exit"],
                                                                 "lag3": rec[3]["ret"]}
                    key = f"{stake}|trig+{land}|{'fast' if dl == 1 else 'slow'}|{name}"
                    s = {"n": len(rows)}
                    for k in ["paper"] + list(LAGS) + [f"T{l}" for l in TLAGS]:
                        rr = [r[k]["ret"] for r in rows]
                        s[str(k)] = {"mean": st.mean(rr), "median": st.median(rr), "worst": min(rr), "wins": sum(1 for x in rr if x > 0),
                                     "mean_ex_outlier": st.mean([r[k]["ret"] for r in rows if r["b0"] != OUTLIER]),
                                     "pull_first": sum(1 for r in rows if r[k]["exit"] == "pull_first"), "partly_pulled": sum(1 for r in rows if r[k]["exit"] == "partly_pulled")}
                    s["tp_rate"] = sum(1 for r in rows if r["paper"]["why"] == "tp" and r["paper"]["exit"] not in ("buy_reverted", "pull_before_buy")) / len(rows)
                    s["exits_paper"] = dict(collections.Counter(r["paper"]["exit"] for r in rows))
                    s["max_land_after_buy"] = max(max(r["paper"]["lands"]) for r in rows)
                    s["land_dist"] = dict(collections.Counter(max(r["paper"]["lands"]) for r in rows if r["paper"]["exit"] not in ("buy_reverted", "pull_before_buy")))
                    s["crossed"] = sum(1 for r in rows if r["paper"].get("crossed"))
                    out["summary"][key] = s
    for (b0, stake, land, dl), v in per.items():
        out["per_launch"].append({"block": b0, "stake": stake, "land": land, "dl": dl, "variants": v})
    json.dump(out, open(os.path.join(HERE, "exits_bt.json"), "w"), indent=1, default=str)

    for dl in (1, 2):
        for stake in STAKES:
            for land in LANDS:
                print(f"\n=== stake {stake} ETH | our buy lands trigger+{land} | sell lands send+{dl} ({'fast, as every live sell' if dl == 1 else 'slow'}) | n={len(ctxs)}")
                print(f"  {'variant':30s} {'paper: mean  median  ex-outl':>28s}  TP%  land" + "".join(f"{'B+' + str(l):>13s}" for l in LAGS) + "".join(f"{'T+' + str(l):>13s}" for l in TLAGS))
                for name in VARIANTS:
                    s = out["summary"][f"{stake}|trig+{land}|{'fast' if dl == 1 else 'slow'}|{name}"]
                    cells = "".join(f"{100 * s[str(l)]['mean']:+8.2f}% {s[str(l)]['pull_first']:2d}{('+' + str(s[str(l)]['partly_pulled'])) if s[str(l)]['partly_pulled'] else '  ':3s}" for l in LAGS)
                    cells += "".join(f"{100 * s['T' + str(l)]['mean']:+8.2f}% {s['T' + str(l)]['pull_first']:2d}{('+' + str(s['T' + str(l)]['partly_pulled'])) if s['T' + str(l)]['partly_pulled'] else '  ':3s}" for l in TLAGS)
                    pp = s["paper"]
                    print(f"  {name:30s} {100 * pp['mean']:+7.2f}% {100 * pp['median']:+7.2f}% {100 * pp['mean_ex_outlier']:+7.2f}%  {100 * s['tp_rate']:3.0f}%  B+{s['max_land_after_buy']}{cells}")
                print("  cells: mean return, pull-first count (+ split trades with one half pulled); B+k: the pull at our buy block + k; T+k: at the trigger block + k")

if __name__ == "__main__":
    main()
