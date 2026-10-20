"""p06: per launch (102; v0 = the 356-B value-0 launches, val = the longer value launches), the flow in the pool: the launch-tx buys, the
fleet's pumps, the bundle wallets' sells, other buys, outside buys before +60, the pulls of the launch position; and the rule (buy at +60,
sell at +260, C's V3Sim replay) at $15 (0.0058 ETH) and $5 (0.001946 ETH). Offline (p03, p04, p05). -> p06_pools.json, p06_flow.out
Definitions:
- fleet buy: a tx to SwapRouter02 0xcaf681a6, exactInputSingle 04e45aaf, 228 bytes, ETH as value (> 0), priority fee 1 wei (REPORT_V23's
  fingerprint 0xcaf681a6:04e45aaf:228:1), not by an operator wallet below. Txs are fetched for every swap up to +600 only.
- operator wallets of a launch: the launch wallet, the call's address words (1, 3, 7), the array's addresses (the launch-tx buy recipients),
  and the senders of the launch position's pulls.
- bundle sell: a sell (token in) whose tx is from an operator wallet.
- outside buy before +60: a buy of >= 0.0005 ETH at +1..+59 whose tx is not a fleet buy nor from an operator wallet (REPORT_V23's test).
- pull: a Burn (liquidity > 0) of the launch position (owner the PositionManager, ticks -887272..207243); other Burns counted apart.
- pumped: a fleet buy at or after +60 (s04's 'operator buy at/after +W' with the fleet as the operator's pump)."""
import sys, os, json, time, statistics as S, collections as C
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as K
X = K.launches(); E = K.events()
T = {}
for l in open(K.J("p05_txs.jsonl")):
    t = json.loads(l); T[t["hash"]] = t
SPLIT_TS = time.mktime(time.strptime("2026-10-11 13:52:41", "%Y-%m-%d %H:%M:%S")) - time.timezone   # census 2's end
Q15, Q5 = 0.0058, round(5 / K.ETH_USD, 6)
wallet_pools = C.defaultdict(set)
for x in X:
    for e in E[x["pool"]]["ev"]:
        t = T.get(e[-1])
        if t and e[0] == "s": wallet_pools[t["from"][2:].lower()].add(x["pool"])
def txinfo(h):
    t = T.get(h)
    if not t: return None
    inp = t["input"] or "0x"
    return {"from": t["from"][2:].lower(), "to": (t["to"] or "")[2:].lower(), "sel": inp[2:10], "len": (len(inp) - 2) // 2, "value": int(t["value"], 16),
            "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "nonce": int(t["nonce"], 16)}
OUT = []
for x in X:
    o = E[x["pool"]]; lb = x["block"]; c = x["call"]
    ops = {x["from"], c["a1"], c["a3"], c["a7"]} | set(c["addrs"])
    burns = [e for e in o["ev"] if e[0] == "b" and e[8] > 0]
    lp = [e for e in burns if e[5] == K.NPM and e[6] == K.LO and e[7] == K.HI]
    for e in lp:
        ti = txinfo(e[-1])
        if ti: ops.add(ti["from"])
    r = {"tx": x["tx"], "pool": x["pool"], "kind": "v0" if x["len"] == 356 else "val", "len": x["len"], "value": x["value"] / 1e18, "block": lb, "ts": x["ts"],
         "post_census": x["ts"] >= SPLIT_TS, "w1": c["a1"], "n_addrs": c["n_addrs"], "eth2": c["eth2"] / 1e18, "from": x["from"]}
    lt = [e for e in o["ev"] if e[0] == "s" and e[-1] == x["tx"]]
    r["ltx_buys"] = len(lt); r["ltx_eth"] = sum(e[7] for e in lt) / 1e18; r["tick_after_ltx"] = lt[-1][11] if lt else 207243
    fleet, osell, obuy, other_buys, other_sells, unf_b = [], [], [], [], [], []
    for e in o["ev"]:
        if e[0] != "s" or e[-1] == x["tx"]: continue
        off = e[1] - lb; buy = e[7] > 0; eth = abs(e[7]) / 1e18; ti = txinfo(e[-1])
        if ti is None:
            if buy: unf_b.append((off, eth, e[6]))
            continue
        isfleet = buy and ti["to"] == K.ROUTER and ti["sel"] == "04e45aaf" and ti["len"] == 228 and ti["value"] > 0 and ti["prio"] == 1 and ti["from"] not in ops
        rec = (off, eth, ti["from"], ti["nonce"], ti["to"][:8], ti["sel"], ti["len"], ti["prio"], ti["value"] > 0)
        if isfleet: fleet.append(rec)
        elif ti["from"] in ops: (obuy if buy else osell).append(rec)
        elif buy: other_buys.append(rec)
        else: other_sells.append(rec)
    r.update({"fleet": fleet, "op_sells": osell, "op_buys": obuy, "other_buys": other_buys, "other_sells": other_sells, "unfetched_buys": unf_b})
    r["first_fleet"] = fleet[0][0] if fleet else None
    r["pumped"] = any(f[0] >= 60 for f in fleet)
    r["fleet_hold"] = [f for f in fleet if 60 <= f[0] < 260]
    r["outside_pre60"] = [b for b in other_buys if 1 <= b[0] < 60 and b[1] >= 0.0005]
    r["outside_pre60_any"] = [b for b in other_buys if 1 <= b[0] < 60]
    r["pulls"] = [(e[1] - lb, e[8], e[8] / K.LINE_L) for e in lp]
    r["first_pull"] = lp[0][1] - lb if lp else None
    r["other_burns"] = [(e[1] - lb, e[5], e[6], e[7], e[8]) for e in burns if e not in lp]
    r["pull_tx"] = [txinfo(e[-1]) for e in lp[:1]]
    r["other_mints"] = [(e[1] - lb, e[5], e[6], e[7], e[8]) for e in o["ev"] if e[0] == "mi" and e[-1] != x["tx"]]
    # price at +60 (tick of the last swap before +60) against the launch-tx end
    pre = [e for e in o["ev"] if e[0] == "s" and e[1] < lb + 60]
    r["tick_at60"] = pre[-1][11] if pre else 207243
    for q, lab in ((Q15, "q15"), (Q5, "q5")):
        r[lab] = K.trade(x, o, 60, 260, q)
    OUT.append(r)
json.dump(OUT, open(K.J("p06_pools.json"), "w"))
# ------------------------------------------------------------------ report
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
pct = lambda v, k: sorted(v)[min(len(v) - 1, int(k * len(v)))] if v else None
def q3(v, nd=3): return "-" if not v else "/".join(f"{pct(v, k):.{nd}f}" if isinstance(pct(v, k), float) else str(pct(v, k)) for k in (0.1, 0.5, 0.9))
def stats(rs, lab, key="q15"):
    xs = [r[key] for r in rs if r[key] and r[key].get("ok")]
    skip = sum(1 for r in rs if r[key] is None)
    if not xs: P(f"  {lab}: n 0 (skipped for a pull before the buy: {skip})"); return None
    rt = [x["ret"] for x in xs]; q = xs[0]["q"]; usd = q * K.ETH_USD
    srt = sorted(rt, reverse=True); tot = sum(rt)
    o = {"n": len(rt), "mean": S.mean(rt), "median": S.median(rt), "win": sum(1 for a in rt if a > 0) / len(rt), "pulled": sum(x["pulled"] for x in xs), "worst": min(rt), "best": max(rt),
         "usd_trade": S.mean(rt) * usd, "tot_usd": tot * usd, "top10": (sum(srt[:max(1, len(rt) // 10)]) / tot) if tot > 0 else None, "skip": skip}
    P(f"  {lab}: n {o['n']} mean {o['mean']*100:+.2f}% median {o['median']*100:+.3f}% win {o['win']*100:.1f}% pulled {o['pulled']} ({o['pulled']/o['n']*100:.1f}%) "
      f"worst {o['worst']*100:+.1f}% best {o['best']*100:+.1f}% | ${o['usd_trade']:.3f}/trade, total ${o['tot_usd']:.2f} | skipped (pull <= buy-2) {skip}"
      + (f" | top 10% of trades = {o['top10']*100:.0f}% of the return" if o["top10"] else ""))
    return o
f = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
for kind, lab in (("v0", "356-B value-0 launches"), ("val", "value launches (548-1828 B)")):
    rs = [r for r in OUT if r["kind"] == kind]
    P(f"\n=== {lab}: n {len(rs)} ({f(rs[0]['ts'])} .. {f(rs[-1]['ts'])} UTC); after census 2's end (Oct 11 13:52 UTC): {sum(r['post_census'] for r in rs)}")
    if kind == "val":
        P(f" launch-tx buys per launch (count) p10/50/90: {q3([r['ltx_buys'] for r in rs], 0)}; ETH {q3([r['ltx_eth'] for r in rs], 2)}; tick after the launch tx {q3([r['tick_after_ltx'] for r in rs], 0)} (launch tick 207243)")
        P(f" tick at +60 (last swap before) p10/50/90: {q3([r['tick_at60'] for r in rs], 0)}; moved from the launch-tx end by {q3([r['tick_at60'] - r['tick_after_ltx'] for r in rs], 0)} ticks")
    fl = [r for r in rs if r["fleet"]]
    P(f" FLEET (fetched to +600): pools with a fleet buy {len(fl)} of {len(rs)} ({len(fl)/len(rs)*100:.0f}%); pumped (a fleet buy at/after +60) {sum(r['pumped'] for r in rs)}; "
      f"with a fleet buy inside the hold +60..+259 {sum(1 for r in rs if r['fleet_hold'])}")
    if fl:
        P(f"   first fleet buy offset p10/50/90 {q3([r['first_fleet'] for r in fl], 0)}; fleet buys per pumped pool (to +600) {q3([len(r['fleet']) for r in fl], 0)}; "
          f"ETH per pool {q3([sum(b[1] for b in r['fleet']) for r in fl], 2)}; ETH per buy {q3([b[1] for r in fl for b in r['fleet']], 3)}")
        P(f"   fleet buys inside the hold per pumped pool {q3([len(r['fleet_hold']) for r in fl], 0)}, ETH {q3([sum(b[1] for b in r['fleet_hold']) for r in fl], 2)}; "
          f"buyer nonce 0: {sum(1 for r in fl for b in r['fleet'] if b[3] == 0)} of {sum(len(r['fleet']) for r in fl)}; buyers in 1 pool only: "
          f"{sum(1 for r in fl for b in r['fleet'] if len(wallet_pools[b[2]]) == 1)}; buyer nonce p10/50/90 {q3([b[3] for r in fl for b in r['fleet']], 0)}; "
          f"distinct fleet wallets {len(set(b[2] for r in fl for b in r['fleet']))}, of them in > 1 pool {sum(1 for w in set(b[2] for r in fl for b in r['fleet']) if len(wallet_pools[w]) > 1)}")
        gaps = [b2[0] - b1[0] for r in fl for b1, b2 in zip(r["fleet"], r["fleet"][1:])]
        P(f"   gap between consecutive fleet buys p10/50/90 {q3(gaps, 0)}")
    os_ = [r for r in rs if r["op_sells"]]
    P(f" OPERATOR WALLETS' SELLS (fetched to +600): pools {len(os_)}; first offset p10/50/90 {q3([r['op_sells'][0][0] for r in os_], 0)}; ETH out per pool to +600 "
      f"{q3([sum(b[1] for b in r['op_sells']) for r in os_], 2)}; inside the hold {q3([sum(b[1] for b in r['op_sells'] if 60 <= b[0] < 260) for r in os_], 2)}; "
      f"calls {C.Counter((b[4], b[5], b[6]) for r in os_ for b in r['op_sells']).most_common(3)}")
    ob = [r for r in rs if r["op_buys"]]
    P(f" OPERATOR WALLETS' BUYS after the launch tx: pools {len(ob)}; ETH {q3([sum(b[1] for b in r['op_buys']) for r in ob], 3)}")
    P(f" OTHER BUYS (not fleet/operator; fetched to +600): in the hold +60..+259: pools {sum(1 for r in rs if any(60 <= b[0] < 260 for b in r['other_buys']))}, "
      f"ETH total {sum(b[1] for r in rs for b in r['other_buys'] if 60 <= b[0] < 260):.4f}, buys >= 0.01 ETH {sum(1 for r in rs for b in r['other_buys'] if 60 <= b[0] < 260 and b[1] >= 0.01)}; "
      f"top calls {C.Counter((b[4], b[5], b[6], b[7]) for r in rs for b in r['other_buys'] if 60 <= b[0] < 260).most_common(4)}")
    P(f" OUTSIDE BUYS >= 0.0005 ETH at +1..+59: pools {sum(1 for r in rs if r['outside_pre60'])}; max {max([b[1] for r in rs for b in r['outside_pre60_any']] or [0]):.5f} ETH; "
      f"callers {C.Counter((b[4], b[5], b[6]) for r in rs for b in r['outside_pre60']).most_common(4)}")
    for flag, nm in ((True, "with"), (False, "without")):
        g = [r for r in rs if bool(r["outside_pre60"]) == flag]
        P(f"   {nm} an outside buy before +60: n {len(g)}, pumped {sum(r['pumped'] for r in g)}; rule $15 mean "
          + (f"{S.mean([r['q15']['ret'] for r in g if r['q15'] and r['q15'].get('ok')])*100:+.2f}%" if [r for r in g if r['q15'] and r['q15'].get('ok')] else "-"))
    pl = [r for r in rs if r["first_pull"] is not None]
    P(f" PULLS of the launch position (to +3000): {len(pl)} of {len(rs)}; first pull offset p10/50/90 {q3([r['first_pull'] for r in pl], 0)}; <= +260: "
      f"{sum(1 for r in pl if r['first_pull'] <= 260)}; <= +300: {sum(1 for r in pl if r['first_pull'] <= 300)}; full (all L): {sum(1 for r in pl if abs(r['pulls'][0][2] - 1) < 1e-9)}")
    P(f"   pull calls {C.Counter((p_['to'][:8], p_['sel'], p_['len'], p_['value'] > 0) for r in pl for p_ in r['pull_tx'] if p_).most_common(3)}; "
      f"pull from: launch wallet {sum(1 for r in pl for p_ in r['pull_tx'] if p_ and p_['from'] == r['from'])}, the call's address word 1 {sum(1 for r in pl for p_ in r['pull_tx'] if p_ and p_['from'] == r['w1'])}; "
      f"distinct pullers {C.Counter(p_['from'][:8] for r in pl for p_ in r['pull_tx'] if p_).most_common(5)}")
    if fl: P(f"   pull after the last fleet buy (pumped pools): {q3([r['first_pull'] - r['fleet'][-1][0] for r in fl if r['first_pull'] is not None], 0)}")
    P(f" other Burns: {sum(len(r['other_burns']) for r in rs)}; other Mints: {sum(len(r['other_mints']) for r in rs)}")
    P(" RULE buy +60 sell +260 (C's V3Sim):")
    for key in ("q15", "q5"):
        stats(rs, f"{'$15' if key == 'q15' else '$5 '} all", key)
        stats([r for r in rs if r["pumped"]], f"{'$15' if key == 'q15' else '$5 '} pumped", key)
        stats([r for r in rs if not r["pumped"]], f"{'$15' if key == 'q15' else '$5 '} not pumped", key)
        if kind == "v0": stats([r for r in rs if r["post_census"]], f"{'$15' if key == 'q15' else '$5 '} after the census", key)
open(K.J("p06_flow.out"), "w").write("\n".join(L) + "\n")
