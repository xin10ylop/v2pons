"""analyse_20: the four assigned families (+ the wider groups they belong to) and the controls (v2.433, operator A), priced with
common20.Pool (analyse_18's pricer, the exact replay of explore/chk/replay.py on the census) plus, for hook 0x4e346895 (family
0x1eef016f|60956835), the hook's 1.3% tax on the swap OUTPUT both ways (tokens on a buy, ETH on a sell; measured from receipts by
hookfee.py: trader tokens = 0.987 x a1 on 7 buys, router WETH out = 0.987 x a0 on 2 sells) and its companion sell after our buy (the hook's
helper 0x6f02324d sells 84% of the taxed tokens in the same tx; modelled as a sell of 0.84 x 1.3% of our tokens right after our buy).
Writes stats.json."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common20
from common20 import *  # noqa

HOOK_4E = "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544"; HELPER_4E = "0x6f02324d20cc679d0e585290caa6b16bacbc0f77"
common20.HOOK_TAX[HOOK_4E] = 13_000
COMPANION_SHARE = 0.84


class Pool20(Pool):
    """common20.Pool + the 0x4e346895 companion sell after our buy, and hook-helper swaps excluded from buys()"""
    def buys(self):
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"] and x["sender"] != HELPER_4E]

    def fee_at(self, bn):
        # a dynamic-fee (0x800000) pool of hook 0x4e346895 with no swap: the LP fee every swapped pool of its factory 0x1eef016f charged (2000)
        if not self.seq and self.fee_key == 8388608 and self.p["hooks"] == HOOK_4E and self.p["launch_to"] == "0x1eef016f22a943abc7dd11422edee9d235942104":
            return 2000
        return Pool.fee_at(self, bn)

    def trade(self, B, S, stake=STAKE):
        if self.p["hooks"] != HOOK_4E: return Pool.trade(self, B, S, stake)
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": None, "B": B - self.b0, "S": S - self.b0}
        s, L = self.state_through(B)
        fb, fs = self.fee_at(B), self.fee_at(S)
        tokens = v4math.buy_out_int(int(s), L, stake, fb)
        held = tokens - tokens * self.tax // 1_000_000
        s = Q96 / (Q96 / s + net_in(stake, fb) / L)
        sold = int((tokens - held) * COMPANION_SHARE)
        s = s + net_in(sold, fb) * Q96 / L                 # token1 in: sqrtPriceX96 rises by dy * Q96 / L (v4math.sell_out_int)
        if self.pull_bn is not None and self.pull_bn <= S:
            return {"exit": "pulled_first", "ret": (-stake - self.gas) / stake, "B": B - self.b0, "S": S - self.b0, "pull": self.pull_bn - self.b0}
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            L = x["liq"] if x["liq"] else L
            s = self.apply(s, x)
        eth_out = v4math.sell_out_int(int(s), L, held, fs)
        eth_out -= eth_out * self.tax // 1_000_000
        return {"exit": "sold", "ret": (eth_out - stake - self.gas) / stake, "gross": (eth_out - stake) / stake, "B": B - self.b0, "S": S - self.b0,
                "dropped": [], "fee_b": fb, "fee_s": fs}


K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
groups = {k: F[k]["pids"] for k in K}
groups["WIDER launch_to 0x1756c648 (deployer 0x17ad4d45, all 12 7fde822e launches)"] = [p["pid"] for p in P.values() if p["launch_to"] == "0x1756c648a426a5a7548ac42350ce3fa980070e65"]
groups["WIDER launch_to 0x258dd351 (deployer 0x06cb3a68, all 20)"] = [p["pid"] for p in P.values() if p["launch_to"] == "0x258dd351af960bc487532c0108d3f90e8d115369"]
groups["WIDER all 7fde822e launches (5 deployers)"] = [p["pid"] for p in P.values() if p["selector"] == "7fde822e"]
groups["WIDER hook 0x4e346895 (all 7 pools, two launch contracts)"] = [p["pid"] for p in P.values() if p["hooks"] == HOOK_4E]
V = [p["pid"] for p in P.values() if p["known"] == "vbot-v2.433"]
A = [p["pid"] for p in P.values() if p["known"] == "operator-A"]
E = load_events(set(x for v in groups.values() for x in v) | set(V) | set(A))
POOL = {}


def pool(pid):
    if pid not in POOL: POOL[pid] = Pool20(P[pid], E.get(pid), T, M)
    return POOL[pid]


def is_bot(x): return x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"


def real_buys(pl, after=None):
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]


def sched_generic(pl, B): r = real_buys(pl, B); return r[0] if r else None
def sched_bot(pl, B): return next((x for x in pl.buys() if x["bn"] > B and is_bot(x)), None)


def front(pl, sched_fn, hold=20, stake=STAKE):
    lb = pl.b0; B = lb + 1; sb = sched_fn(pl, B)
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= lb + hold) else lb + hold
    r = pl.trade(B, S, stake); r["sched"] = (sb["bn"] - lb) if sb else None; return r


def follow(pl, hold=4, stake=STAKE):
    lb = pl.b0; rb = real_buys(pl)
    if not rb: return None
    trig = rb[0]; B = trig["bn"] + 1
    nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
    r = pl.trade(B, S, stake); r.update({"pid": pl.pid, "trig": trig["bn"] - lb, "trig_eth": trig["eth"] / 1e18, "next": (nxt["bn"] - lb) if nxt else None}); return r


def capacity(pl, sb):
    s, L = pl.launch_state(); fee = pl.fee_at(sb["bn"]); Y = sb["eth"]
    quote = v4math.buy_out_int(int(s), L, Y, fee)
    if is_bot(sb) and sb["input"]:
        mo = word(sb["input"], 4); src = "calldata word 4 (bot router c1120e3d)"
    elif sb["to"] == UR:
        mo = int(quote * 0.99); src = "Universal Router execute (nested, not decoded): ASSUMED minOut = 0.99 x launch-state quote"
    else:
        mo = int(quote * 0.99); src = "router %s sel %s not decoded: ASSUMED minOut = 0.99 x launch-state quote" % ((sb["to"] or "?")[:10], sb["sel"])
    return {"cap_eth": room(s, L, Y, fee, mo), "src": src, "minout_over_quote": mo / quote if quote else None, "Y": Y / 1e18}


out = {}
# ------------------------------------------------------------------ controls (calibrate the method)
C = {}
rs = [front(pool(x), sched_bot) for x in V]
C["v2433_front_all"] = summarize(rs)
C["v2433_sched_off_p10_50_90"] = q([r["sched"] for r in rs if r["sched"] is not None])
lw = [r for x, r in zip(V, rs) if 84880000 <= P[x]["launch_block"] <= 84970000]
C["v2433_front_livewindow_oct10_0907_1139"] = summarize(lw)
C["v2433_front_generic_sched"] = summarize([front(pool(x), sched_generic) for x in V])
caps = [capacity(pool(x), sb) for x in V for sb in [sched_bot(pool(x), P[x]["launch_block"])] if sb]
C["v2433_capacity_p10_50_90"] = q([c["cap_eth"] for c in caps])
C["v2433_minout_over_quote_p10_50_90"] = q([c["minout_over_quote"] for c in caps])
diffs = []
for x in V + A:
    pl = pool(x); rel = [y for y in pl.seq if y["relay"]]
    rb = [y for y in rel if y["buy"]]; rsl = [y for y in rel if not y["buy"]]
    if len(rb) != 1 or len(rsl) != 1: continue
    b, s = rb[0], rsl[0]; real = (s["eth"] - b["eth"]) / b["eth"]
    before_in_S = any(y["bn"] == s["bn"] and y["li"] < s["li"] and not y["relay"] for y in pl.seq)
    sim = pl.trade(b["bn"], s["bn"] + (1 if before_in_S else 0), stake=b["eth"])
    if sim.get("gross") is not None: diffs.append((sim["gross"] - real, real, sim["gross"], P[x]["known"]))
d = [z[0] for z in diffs]
C["live_relay_calibration"] = {"n": len(diffs), "real_mean": st.mean(z[1] for z in diffs), "model_mean": st.mean(z[2] for z in diffs),
                               "diff_p10_50_90": q(d, nd=7), "abs_diff_median": st.median(abs(z) for z in d), "within_0.5pt": sum(1 for z in d if abs(z) < 0.005)}
fa = [r for r in (follow(pool(x)) for x in A) if r]
C["opA_follow"] = summarize(fa); C["opA_follow_trig_p10_50_90"] = q([r["trig"] for r in fa])
C["opA_front_generic"] = summarize([front(pool(x), sched_generic) for x in A])
C["gas_usd_per_trade_v2433_median"] = st.median(pool(x).gas for x in V) / 1e18 * USD_PER_ETH
out["controls"] = C
print("CONTROLS")
for k, v in C.items(): print("  ", k, fmt_rule(v) if isinstance(v, dict) and "exits" in v else v)

# ------------------------------------------------------------------ families
for g, pids in groups.items():
    pls = [pool(x) for x in pids]; ps = [P[x] for x in pids]
    lbs = [p["launch_block"] for p in ps]
    r = {"count": len(ps), "launches_per_day": round(len(ps) / WINDOW_DAYS, 2),
         "first_last_block": [min(lbs), max(lbs)], "span_hours": round((max(lbs) - min(lbs)) * 0.1026 / 3600, 2),
         "deployers": collections.Counter(p["launch_from"] for p in ps).most_common(5), "n_deployers": len(set(p["launch_from"] for p in ps)),
         "launch_to": collections.Counter(p["launch_to"] for p in ps).most_common(3), "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(3),
         "fees": collections.Counter(p["fee"] for p in ps).most_common(4), "hooks": collections.Counter(p["hooks"] for p in ps).most_common(3),
         "calldata_len": collections.Counter(p["calldata_len"] for p in ps).most_common(4),
         "nonce_range": [min(p["launch_nonce"] for p in ps), max(p["launch_nonce"] for p in ps)],
         "tick0": collections.Counter(p["tick0"] for p in ps).most_common(3), "liq_launch": collections.Counter(p["liq_launch"] for p in ps).most_common(3),
         "start": collections.Counter(pl.start for pl in pls).most_common(),
         "buy_in_launch_tx": sum(1 for p in ps if p["buy_in_launch_tx"])}
    fb = [(pl, pl.buys()[0]) for pl in pls if pl.buys()]
    r["first_buy_any"] = {"pools_with": len(fb), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fb]), "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fb], nd=8),
                          "to": collections.Counter(x["to"] for pl, x in fb).most_common(3), "from": collections.Counter(x["from"] for pl, x in fb).most_common(3),
                          "n_from": len(set(x["from"] for pl, x in fb))}
    fr = [(pl, real_buys(pl)[0]) for pl in pls if real_buys(pl)]
    r["first_buy_real"] = {"pools_with": len(fr), "frac": round(len(fr) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in fr]), "eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in fr]),
                           "to": collections.Counter(x["to"] for pl, x in fr).most_common(4), "from": collections.Counter(x["from"] for pl, x in fr).most_common(4),
                           "n_from": len(set(x["from"] for pl, x in fr)), "by_launch_wallet": sum(1 for pl, x in fr if x["from"] == pl.p["launch_from"]),
                           "list": [(pl.pid[:12], x["bn"] - pl.b0, x["eth"] / 1e18, x["to"], x["from"], x["sel"], x["nonce"]) for pl, x in fr][:12]}
    allsw = [x for pl in pls for x in pl.seq]
    r["swaps"] = {"total": len(allsw), "buys": sum(1 for x in allsw if x["buy"]), "sells": sum(1 for x in allsw if not x["buy"]),
                  "eth_in": sum(x["eth"] for x in allsw if x["buy"]) / 1e18, "from": collections.Counter(x["from"] for x in allsw).most_common(5),
                  "pools_with_any": sum(1 for pl in pls if pl.seq), "pools_with_sell": sum(1 for pl in pls if any(not x["buy"] for x in pl.seq))}
    pl_ = [(pl, pl.pulls[0]) for pl in pls if pl.pulls]
    r["pull"] = {"pulled_3000": len(pl_), "frac": round(len(pl_) / len(pls), 3), "off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in pl_]),
                 "off_from_first_real_buy_p10_50_90": q([x["bn"] - real_buys(pl)[0]["bn"] for pl, x in pl_ if real_buys(pl)]),
                 "by": collections.Counter(pl.p["first_pull_from"] for pl, x in pl_).most_common(3),
                 "by_launch_wallet": sum(1 for pl, x in pl_ if pl.p["first_pull_from"] == pl.p["launch_from"])}
    # trap test: outsider = a buy (any size, the chain-wide dust wallets counted apart) by a non-launch wallet before the first scheduled (real) buy
    wo, wi, dust_only = [], [], 0
    for pl in pls:
        sb = sched_generic(pl, pl.b0)
        pre = [x for x in pl.buys() if (sb is None or (x["bn"], x["li"]) < (sb["bn"], sb["li"])) and x["from"] != pl.p["launch_from"]]
        outs = [x for x in pre if x["from"] not in DUST_WALLETS]
        if pre and not outs: dust_only += 1
        pb = pl.pull_bn
        if outs: wi.append((pb - outs[0]["bn"]) if pb is not None else None)
        else: wo.append((pb - pl.b0) if pb is not None else None)
    r["trap"] = {"pools_with_outsider_before_sched": len(wi), "pools_with_only_dust_wallet_before_sched": dust_only, "pulled_after_outsider": sum(1 for z in wi if z is not None),
                 "delay_after_outsider_p10_50_90": q([z for z in wi if z is not None]), "pools_without": len(wo),
                 "pulled_without": sum(1 for z in wo if z is not None), "pull_off_without_p10_50_90": q([z for z in wo if z is not None])}
    frs = [front(pl, sched_generic) for pl in pls]
    r["front"] = summarize(frs); r["front_sched_by_20"] = sum(1 for z in frs if z.get("sched") is not None and z["sched"] + 1 <= 20)
    r["front_gross_p10_50_90"] = q([z["gross"] for z in frs if z.get("gross") is not None])
    r["front_hold3000"] = summarize([front(pl, sched_generic, hold=3000) for pl in pls])
    fos = [z for z in (follow(pl) for pl in pls) if z]
    r["follow"] = summarize(fos); r["follow_rows"] = [{k: z.get(k) for k in ("pid", "trig", "trig_eth", "next", "B", "S", "exit", "ret", "gross", "fee_b", "fee_s")} for z in fos][:12]
    caps = [capacity(pl, sb) for pl in pls for sb in [sched_generic(pl, pl.b0)] if sb]
    r["capacity"] = {"n": len(caps), "cap_eth_p10_50_90": q([c["cap_eth"] for c in caps]), "rows": caps[:8], "src": collections.Counter(c["src"] for c in caps).most_common(2)}
    r["gas_usd_median"] = st.median(pl.gas for pl in pls) / 1e18 * USD_PER_ETH
    out[g] = r
    print("=" * 110); print(g)
    for k, v in r.items():
        if k in ("front", "follow", "front_hold3000"): print("  %-22s %s" % (k, fmt_rule(v)))
        else: print("  %-22s %s" % (k, v))
json.dump(out, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
