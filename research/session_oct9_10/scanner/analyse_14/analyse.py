import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14")
from common14 import *

KEYS = ["0x34c0d66f3a57a4cad3c5f792f5028d9c1da83d12|f03e0011|292|0|200|false",
        "0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|772|10000|200|true",
        "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|500000|5000|true",
        "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|810000|8100|true"]
P0 = load_pools(); F = load_families()
TAX = {KEYS[0]: 12_500}   # hook 0xbba868de takes 1.25% of the ETH in (tx value x 0.9875 = Swap a0 on every buy, 9 of 9)
DECOYS = ("0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758")
groups = {k: F[k]["pids"] for k in KEYS}
groups["CONTROL vbot-v2.433"] = [p["pid"] for p in P0.values() if p["known"] == "vbot-v2.433"]
groups["CONTROL operator-A"] = [p["pid"] for p in P0.values() if p["known"] == "operator-A"]
allp = set(x for v in groups.values() for x in v)
ctx = Ctx(allp)
P, E, T = ctx.P, ctx.E, ctx.T


def buys_of(p):
    e = E.get(p["pid"])
    if not e: return []
    return [s for s in e["swaps"] if s["a0"] < 0 and s["tx"] != p["launch_tx"] and s["sender"] != RELAY]


def txinfo(h):
    t = T.get(h)
    return (t["to"], t["from"], t["selector"]) if t else (None, None, None)


def sched_buy(p, control):
    bs = buys_of(p)
    if control == "vbot":
        for s in bs:
            if is_bot_buy(T.get(s["tx"])): return s
        return None
    for s in bs:
        if -s["a0"] >= MIN_REAL: return s
    return None


def capacity(p, sb):
    """ETH (gross, at the launch state) that can sit ahead of the scheduled buy sb before its output falls under its minOut"""
    e = E[p["pid"]]; fee = pool_fee(p, e); L = p["liq_launch"]; sp = p["sqrt_p0"]; Y = -sb["a0"]
    if L <= 0: return None, None
    t = T.get(sb["tx"])
    quote = v4math.buy_out_int(sp, L, Y, fee)
    if is_bot_buy(t):
        mo = bot_minout(t); src = "decoded minOut (c1120e3d word 4)"
    else:
        mo = int(quote * 0.99); src = "ASSUMED minOut = 0.99 x launch-state quote"
    def out_after(A):
        s2 = Q96 / (Q96 / sp + net(A, fee) / L)
        return v4math.buy_out_int(int(s2), L, Y, fee)
    if out_after(0) < mo: return 0.0, src + " (fails even with nothing ahead)"
    lo, hi = 0, int(100e18)
    if out_after(hi) >= mo: return 100.0, src
    while hi - lo > 10**12:
        m = (lo + hi) // 2
        if out_after(m) >= mo: lo = m
        else: hi = m
    return lo / 1e18, src + " minOut/quote %.4f" % (mo / quote if quote else 0)


out = {}
for key, pids in groups.items():
    control = "vbot" if "v2.433" in key else ("opA" if "operator-A" in key else None)
    pools = sorted([P[x] for x in pids], key=lambda p: p["launch_block"])
    n = len(pools)
    span_days = DAYS
    fam = {"key": key, "count": n, "launches_per_day": round(n / span_days, 2)}
    # launcher
    fr = collections.Counter(p["launch_from"] for p in pools); vals = collections.Counter(round(p["launch_value_eth"], 6) for p in pools)
    fam["launcher"] = {"to": collections.Counter(p["launch_to"] for p in pools).most_common(3), "selector": collections.Counter(p["selector"] for p in pools).most_common(3),
                       "calldata_len": collections.Counter(p["calldata_len"] for p in pools).most_common(3), "values": vals.most_common(6),
                       "n_from": len(fr), "top_from": fr.most_common(4), "nonce_p10_50_90": pct([p["launch_nonce"] for p in pools]),
                       "hooks": collections.Counter(p["hooks"] for p in pools).most_common(2), "fees": collections.Counter(p["fee"] for p in pools).most_common(4),
                       "buy_in_launch_tx": sum(1 for p in pools if p["buy_in_launch_tx"]), "liq_launch_zero": sum(1 for p in pools if not p["liq_launch"]),
                       "first_ts": pools[0]["launch_ts"], "last_ts": pools[-1]["launch_ts"]}
    # first non-launch buy (any size) and first real buy
    fb_rows = []
    for p in pools:
        bs = buys_of(p)
        if not bs: continue
        s = bs[0]; to, frm, sel = txinfo(s["tx"])
        fb_rows.append({"off": s["bn"] - p["launch_block"], "eth": -s["a0"] / 1e18, "to": to, "from": frm, "sel": sel, "launch_from": p["launch_from"]})
    real_rows = []
    for p in pools:
        bs = [s for s in buys_of(p) if -s["a0"] >= MIN_REAL]
        if not bs: continue
        s = bs[0]; to, frm, sel = txinfo(s["tx"])
        real_rows.append({"off": s["bn"] - p["launch_block"], "eth": -s["a0"] / 1e18, "to": to, "from": frm, "sel": sel, "is_launcher": frm == p["launch_from"]})
    def fbsum(rows):
        if not rows: return {"frac_pools": 0.0}
        return {"frac_pools": round(len(rows) / n, 3), "off_p10_50_90": pct([r["off"] for r in rows]), "eth_p10_50_90": [round(x, 7) for x in pct([r["eth"] for r in rows])],
                "to_top": collections.Counter((r["to"], r["sel"]) for r in rows).most_common(4), "n_from": len(set(r["from"] for r in rows)),
                "from_top": collections.Counter(r["from"] for r in rows).most_common(3), "from_is_launcher": sum(1 for r in rows if r["from"] == r.get("launch_from") or r.get("is_launcher"))}
    fam["first_buy_any"] = fbsum(fb_rows); fam["first_buy_real"] = fbsum(real_rows)
    # scheduled buy
    sched = {p["pid"]: sched_buy(p, control) for p in pools}
    # pulls
    pr = []
    for p in pools:
        e = E.get(p["pid"]); pl = e["pulls"] if e else []
        if not pl: continue
        sb = sched[p["pid"]]
        pr.append({"off": pl[0]["bn"] - p["launch_block"], "after_sched": (pl[0]["bn"] - sb["bn"]) if sb and sb["bn"] <= pl[0]["bn"] else None,
                   "by_launcher": p["first_pull_from"] == p["launch_from"], "to": p["first_pull_to"], "sel": p["first_pull_selector"]})
    fam["pull"] = {"frac_pulled_3000": round(len(pr) / n, 3), "off_launch_p10_50_90": pct([r["off"] for r in pr]),
                   "off_sched_buy_p10_50_90": pct([r["after_sched"] for r in pr if r["after_sched"] is not None]),
                   "by_launch_wallet": sum(1 for r in pr if r["by_launcher"]), "n": len(pr), "to_sel": collections.Counter((r["to"], r["sel"]) for r in pr).most_common(3)}
    # outsiders before the scheduled buy, trap test
    with_out, without = [], []; pre_with, pre_without = [], []; n_dust = [0]
    out_sizes = []
    for p in pools:
        sb = sched[p["pid"]]; e = E.get(p["pid"])
        if not e: continue
        lim = sb["bn"] if sb else p["launch_block"] + 3001
        outs = []
        for s in buys_of(p):
            if (s["bn"], s["li"]) >= ((sb["bn"], sb["li"]) if sb else (lim, 0)): break
            to, frm, sel = txinfo(s["tx"])
            if frm == p["launch_from"]: continue
            if -s["a0"] < 1e13: n_dust[0] += 1; continue                       # dust (< 1e-5 ETH: the chain-wide 2e-6 dust bot 0xe71a69f4 and the like)
            if control == "vbot" and to in DECOYS: continue                      # the volume bot's decoy routers
            outs.append(s)
        pl = e["pulls"][0]["bn"] if e["pulls"] else None
        pre = (pl is not None and sb is not None and pl < sb["bn"]) or (pl is not None and sb is None and outs and pl - outs[0]["bn"] <= 20)
        (pre_with if outs else pre_without).append(bool(pre))
        if outs:
            out_sizes.append(-outs[0]["a0"] / 1e18)
            with_out.append((pl - outs[0]["bn"]) if pl and pl >= outs[0]["bn"] else None)
        else:
            without.append((pl - sb["bn"]) if (pl and sb and pl >= sb["bn"]) else ((pl - p["launch_block"]) if pl else None))
    fam["outsiders"] = {"frac_pools": round(len(with_out) / n, 3), "size_p10_50_90": pct(out_sizes),
                        "pull_after_outsider_p10_50_90": pct([x for x in with_out if x is not None]), "pulled_with": sum(1 for x in with_out if x is not None), "n_with": len(with_out),
                        "pull_delay_without_p10_50_90": pct([x for x in without if x is not None]), "pulled_without": sum(1 for x in without if x is not None), "n_without": len(without),
                        "pulled_before_sched_with": sum(pre_with), "pulled_before_sched_without": sum(pre_without), "dust_buys_skipped": n_dust[0]}
    # front rule
    fr_rows = []
    for p in pools:
        lb = p["launch_block"]; sb = sched[p["pid"]]
        if sb and sb["bn"] <= lb + 1:
            fr_rows.append({"pid": p["pid"], "exit": "late_sched_at_or_before_+1", "ret": None}); continue
        S = min(sb["bn"] + 1, lb + 20) if sb else lb + 20
        r = replay(ctx, p, lb + 1, S, tax_ppm=TAX.get(key, 0)); r["pid"] = p["pid"]; r["sched"] = (sb["bn"] - lb, -sb["a0"] / 1e18) if sb else None
        fr_rows.append(r)
    fam["front"] = summ(fr_rows, n); fam["front"]["exits"] = dict(collections.Counter(r["exit"] for r in fr_rows))
    # follow rule
    fo_rows = []
    for p in pools:
        lb = p["launch_block"]
        bs = [s for s in buys_of(p) if -s["a0"] >= MIN_REAL]
        if not bs: continue
        B = bs[0]["bn"] + 1
        nxt = [s for s in bs if s["bn"] > B]
        S = min(nxt[0]["bn"] + 1, B + 4) if nxt else B + 4
        r = replay(ctx, p, B, S, tax_ppm=TAX.get(key, 0)); r["pid"] = p["pid"]; fo_rows.append(r)
    fam["follow"] = summ(fo_rows, n); fam["follow"]["exits"] = dict(collections.Counter(r["exit"] for r in fo_rows))
    # capacity
    caps = []
    for p in pools:
        sb = sched[p["pid"]]
        if not sb: continue
        c, src = capacity(p, sb)
        if c is not None: caps.append((c, src))
    fam["capacity"] = {"n": len(caps), "eth_p10_50_90": pct([c for c, _ in caps]), "src": collections.Counter(s.split(" minOut/quote")[0] for _, s in caps).most_common(2),
                       "ratio_examples": [s for _, s in caps[:3]]}
    fam["_front_rows"] = fr_rows[:12]; fam["_follow_rows"] = fo_rows[:12]
    out[key] = fam
    print("=" * 110); print(key, n, "per day", fam["launches_per_day"])
    for k in ("launcher", "first_buy_any", "first_buy_real", "pull", "outsiders", "front", "follow", "capacity"):
        print(" ", k, json.dumps(fam[k], default=str)[:900])
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14/results_raw.json", "w"), indent=1, default=str)
clean = {k: {x: y for x, y in v.items() if not x.startswith("_")} for k, v in out.items()}
json.dump(clean, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14/results.json", "w"), indent=1, default=str)
