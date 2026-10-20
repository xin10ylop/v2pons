"""B05: REPORT_S's "Gate for a $5 probe" re-run on the last 6 h and the last 24 h to the frozen b01 head (and the 56 h for context).
Items: (1) line launches; (2) the own first buy's size (0.05 share, any 0.001, any launch lacking an own buy by +200) and its shape;
(3) mint -> own buy gap, own buy offset, dEaD transfer -> buy gap, in blocks and seconds; (4) pulls at or before the own buy + 3;
(5) outsider buys between the mint and the own buy, and what the launcher did; (6) rule (a) replayed with C/replay.py's V3Sim:
buy at the head of the mint + 2, sell at the head of min(own first buy + 1, +200) (a pull at or before the sell = -100%), at $5 and $15,
ETH $2570 and gas $0.02 per round trip as in REPORT_S. Also (a,k3) sell at own + 3, and (a,L) = (a) skipping mints with L < 1e22.
-> b05_gate.out, b05_gate.json"""
import statistics as st
from collections import Counter
from bc import *
from replay import replay, V3Sim, ETH_USD, GAS_USD
M, RR = load(); TH = M["t_head"]; HEAD = M["head"]
LR = [r for r in RR if r["line"]]
QS = {"$5": 0.00195, "$15": 0.0058}
BT = Cache("b01_bt")
bt = block_ts(BT, [b for r in LR for b in ([r["lb"], r["lb"] + r["mints"][0]["off"]] + ([r["lb"] + r["own1"]["off"]] if r["own1"] else [])
                                            + ([r["lb"] + r["dead_off"]] if r["dead_off"] is not None else []))])
def own_ok_shape(r):
    o = r["own1"]
    return bool(o) and o.get("to") == SR02 and o.get("sel") == "04e45aaf" and o.get("len") == 228 and o.get("min_out") == 0 and \
        o.get("recipient") == r["lw"] and abs(o.get("value", 0) - o["eth"]) < 1e-12 and o.get("type") == "0x0"
def own200(r): return r["own1"] if r["own1"] and r["own1"]["off"] <= 200 else None
def plans(r):
    m = r["mints"][0]["off"]; o = own200(r); a = m + 2
    b = min(o["off"] + 1, 200) if o and o["off"] >= a else 200
    b3 = min(o["off"] + 3, 200) if o and o["off"] >= a else 200
    P = {"(a) own+1 cap 200": (a, b), "(a,k3) own+3 cap 200": (a, b3)}
    if r["mints"][0]["L"] >= 1e22: P["(a,L) L>=1e22 only"] = (a, b)
    return P
res = {}
for r in LR:
    for name, (a, b) in plans(r).items():
        for ql, q in QS.items():
            x = replay({"dex": "v3", "quote_side": r["qs"], "fee": r["fee"]}, {"lb": r["lb"], "ev": r["ev"], "ev_to": r["ev_to"]}, a, b, q)
            if x["ok"]: res[(r["pool"], name, ql)] = dict(x, a=a, b=b)
# simulator check: the own first buy re-simulated by amount
chk = []
for r in LR:
    o = r["own1"]
    if not o: continue
    sim = V3Sim(r["qs"], r["fee"])
    for e in r["ev"]:
        if e is o["e"]: break
        sim.apply(e)
    chk.append(sim.buy(int(round(o["eth"] * 1e18))) / o["tok"] - 1)
out = [f"head {HEAD} {ts(TH)} UTC (frozen in b01_meta.json); line = fee 100, 13ead562 to 0x73991a25, the one-sided [-887272,204200] (or mirrored) "
       f"mint by the launch wallet; ETH ${ETH_USD:.0f}, gas ${GAS_USD} per round trip; $5 = {QS['$5']} ETH, $15 = {QS['$15']} ETH",
       f"simulator check (own first buy re-simulated by amount): n {len(chk)}, |rel err| max {max(abs(x) for x in chk):.2e}"]
def P(s=""): out.append(s)
def q(xs, f="%g"):
    xs = sorted(xs)
    return "-" if not xs else f"n {len(xs)} min {f % xs[0]} med {f % xs[len(xs) // 2]} max {f % xs[-1]}"
J = {}
for wl, hrs in (("last 6 h", 6), ("last 24 h", 24), ("last 56 h (context)", 56)):
    xs = [r for r in LR if TH - r["ts"] <= hrs * 3600]; days = hrs / 24
    P(f"\n=================== {wl}: since {ts(TH - hrs * 3600)} UTC")
    allx = [r for r in RR if TH - r["ts"] <= hrs * 3600]
    P(f"(1) line launches {len(xs)} ({len(xs) / days:.1f}/day), wallets {len(set(r['lw'] for r in xs))}; other 13ead562 WETH-side launches {len(allx) - len(xs)} "
      f"({Counter((r['lw'][:10], r['fee']) for r in allx if not r['line']).most_common()})")
    P(f"    L tiers {Counter('%.4g' % r['mints'][0]['L'] for r in xs).most_common()}")
    sz = Counter(round(own200(r)["eth"], 4) if own200(r) else None for r in xs)
    n05 = sum(1 for r in xs if own200(r) and abs(own200(r)["eth"] - 0.05) < 1e-9)
    P(f"(2) own first buy by +200: {sz.most_common()}; 0.05 share {n05}/{len(xs)} = {n05 / max(len(xs), 1):.2f}; 0.001: {sz.get(0.001, 0)}; "
      f"lacking an own buy by +200: {sum(1 for r in xs if not own200(r))} {[(r['lw'][:10], r['lb'], ('own1 +%d %.4f' % (r['own1']['off'], r['own1']['eth'])) if r['own1'] else 'none to +%d' % (r['ev_to'] - r['lb'])) for r in xs if not own200(r)]}")
    P(f"    own-buy shape (SR02 04e45aaf 228 B, value = amountIn, minOut 0, recipient = the launch wallet, type 0): {sum(own_ok_shape(r) for r in xs if own200(r))}/{sum(1 for r in xs if own200(r))}")
    ys = [r for r in xs if own200(r)]
    gap = [r["own1"]["off"] - r["mints"][0]["off"] for r in ys]
    P(f"(3) mint offset {q([r['mints'][0]['off'] for r in xs], '%d')}; own buy offset {q([r['own1']['off'] for r in ys], '%d')}; mint -> own buy {q(gap, '%d')} blocks; "
      f">= 10 blocks: {sum(g >= 10 for g in gap)}/{len(gap)}; own <= +190: {sum(r['own1']['off'] <= 190 for r in ys)}/{len(ys)}")
    P(f"    dEaD transfer offset {q([r['dead_off'] for r in xs if r['dead_off'] is not None], '%d')}; missing {sum(1 for r in xs if r['dead_off'] is None)}; "
      f"transfer -> own buy {q([r['own1']['off'] - r['dead_off'] for r in ys if r['dead_off'] is not None], '%d')} blocks, "
      f"{q([bt[r['lb'] + r['own1']['off']] - bt[r['lb'] + r['dead_off']] for r in ys if r['dead_off'] is not None], '%d')} s; "
      f"launch -> own buy {q([bt[r['lb'] + r['own1']['off']] - bt[r['lb']] for r in ys], '%d')} s; mint -> own buy {q([bt[r['lb'] + r['own1']['off']] - bt[r['lb'] + r['mints'][0]['off']] for r in ys], '%d')} s")
    early = [r for r in xs if r["pull1"] and r["pull1"]["off"] <= (own200(r)["off"] + 3 if own200(r) else 203)]
    pl = [r for r in xs if r["pull1"]]
    P(f"(4) pulls at or before the own buy + 3 (or +203 without one): {len(early)} {[(r['lw'][:10], r['pull1']['off']) for r in early]}; "
      f"pulled by +{min(5000, HEAD - xs[0]['lb']) if xs else 0}: {len(pl)}/{len(xs)} at {sorted(r['pull1']['off'] for r in pl)}, by the launch wallet {sum(r['pull1']['by_lw'] for r in pl)}")
    pre = [r for r in xs if any(s["off"] >= r["mints"][0]["off"] and s["off"] <= (r["own1"]["off"] if r["own1"] else 200) for s in r["pre"])]
    P(f"(5) outsider buys between the mint and the own buy (or +200): {len(pre)} " + "; ".join(
        f"{r['lw'][:10]} {r['lb']}: {[(s['off'], round(s['eth'], 5), (s['from'] or '?')[:10]) for s in r['pre']]} -> own1 {('+%d %.4f' % (r['own1']['off'], r['own1']['eth'])) if r['own1'] else 'none'}"
        for r in pre))
    J[wl] = {"n": len(xs), "per_day": len(xs) / days, "n05": n05, "no_own200": sum(1 for r in xs if not own200(r)), "n001": sz.get(0.001, 0),
             "gap_min": min(gap) if gap else None, "own_max": max((r["own1"]["off"] for r in ys), default=None), "early_pulls": len(early), "pre": len(pre)}
    for name in ("(a) own+1 cap 200", "(a,k3) own+3 cap 200", "(a,L) L>=1e22 only"):
        for ql in QS:
            zs = [res[(r["pool"], name, ql)] for r in xs if (r["pool"], name, ql) in res]
            if not zs: continue
            rets = [z["ret"] for z in zs]; usd = [z["usd"] for z in zs]
            P(f"(6) {name:22s} {ql:3s}: n {len(zs)} mean {st.mean(rets) * 100:+.2f}% med {st.median(rets) * 100:+.2f}% win {sum(v > 0 for v in rets) / len(rets):.2f} "
              f"worst {min(rets) * 100:+.2f}% pulled {sum(z['pulled'] for z in zs)} $/trade {st.mean(usd):+.3f} $/day {st.mean(usd) * len(zs) / days:+.2f} "
              f"(trades/day {len(zs) / days:.1f})")
            J[wl][f"{name}|{ql}"] = {"n": len(zs), "mean": st.mean(rets), "win": sum(v > 0 for v in rets) / len(rets), "pulled": sum(z["pulled"] for z in zs),
                                     "usd_trade": st.mean(usd), "usd_day": st.mean(usd) * len(zs) / days}
P("\n=================== every line launch of the last 30 h (newest last): rule (a) [a,b) ret at $5 / $15")
for r in LR:
    if TH - r["ts"] > 30 * 3600: continue
    o = r["own1"]; m = r["mints"][0]; a5 = res.get((r["pool"], "(a) own+1 cap 200", "$5")); a15 = res.get((r["pool"], "(a) own+1 cap 200", "$15"))
    P(f"  {r['lb']} {ts(r['ts'])} {r['lw'][:10]} n{r['nonce']} mint +{m['off']} L {m['L']:.4g} dEaD +{r['dead_off']} own1 "
      f"{('+%d %.4f (%+d s from launch)' % (o['off'], o['eth'], bt[r['lb'] + o['off']] - bt[r['lb']])) if o and o['off'] <= 200 else 'none by +200'} "
      f"pull {('+%d' % r['pull1']['off']) if r['pull1'] else '-'} | (a) [{a5['a']},{a5['b']}) {a5['ret'] * 100:+.2f}% / {a15['ret'] * 100:+.2f}%{' PULLED' if a5['pulled'] else ''}")
open(p("b05_gate.out"), "w").write("\n".join(out) + "\n"); json.dump(J, open(p("b05_gate.json"), "w"), indent=1); print("\n".join(out)); print(R.STATS)
