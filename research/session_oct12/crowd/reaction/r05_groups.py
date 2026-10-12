"""(1) the crowd's and the operator's behaviour in pools where an outside wallet bought >= 0.0005 ETH before the crowd's first real buy,
against pools with no such buyer. Groups: by when the outsider bought (in our landing zone + 1..+ 10, or any time before the crowd),
whether it still held at the crowd's first real buy, and whether it is the recurring + 1 bot (0x776e5a2a) or anyone else. Outcomes: the
crowd came (before the pull, within + 3000), by + 78; its first real buy's offset; its wave (ETH bought in [frb, frb + 20]); the pull
before our sell (min(trigger + 20, + 80)), before the crowd; the rule's return at 0.002 ETH ($5) (analyst C's V3 replay, no reaction modelled)."""
from rlib import *
import collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
Q = float(os.environ.get("Q", "0.002"))     # $5 at ~$2,527 (r10_ethusd.out: 0.00198 ETH)
P = load(); head = json.load(open(J("r01_meta.json")))
BOT1 = "0x776e5a2a"   # prefix of the + 1 bot (via 0x570759db): set after a look at the data
for p in P:
    r = replay({"dex": "v3", "quote_side": p["qs"], "fee": 100}, {"lb": p["lb"], "ev": p["ev"], "ev_to": p["win_to"]}, 2, p["sell"], Q)
    p["ret"] = r.get("ret") if r["ok"] else None; p["pulled_hold"] = p["pull"] is not None and p["pull"] <= p["sell"]
def outcome(lab, ps, fh=None):
    n = len(ps)
    if not n: print(f"  {lab:<58} n 0"); return None
    came = [p for p in ps if p["frb"] is not None]; c78 = sum(1 for p in came if p["frb"] <= 78)
    pb = sum(1 for p in ps if p["pulled_hold"]); pnc = sum(1 for p in ps if p["pull"] is not None and (p["frb"] is None or p["pull"] < p["frb"]) and p["pull"] <= p["end"])
    fr = [p["frb"] for p in came]; wv = [p["wave"] for p in came]; rs = [p["ret"] for p in ps if p["ret"] is not None]
    pl = [p["pull"] for p in ps if p["pull"] is not None]
    lo, hi = wilson(pb, n)
    print(f"  {lab:<58} n {n:>4}  crowd came {len(came)/n:5.1%} by+78 {c78/n:5.1%}  frb p25/50/75 {pct(fr,.25)}/{pct(fr,.5)}/{pct(fr,.75)}  wave med {pct(wv,.5) or 0:.3f} mean {sum(wv)/max(1,len(wv)):.3f}"
          f"  pulled<=sell {pb} ({pb/n:.1%}, CI {lo:.1%}-{hi:.1%})  pulled before crowd {pnc/n:5.1%}  pull med {pct(pl,.5)}  rule mean {sum(rs)/max(1,len(rs))*100:+.2f}% med {(pct(rs,.5) or 0)*100:+.2f}%")
    return {"n": n, "came": len(came), "c78": c78, "pb": pb, "pnc": pnc}
def cmp(lab, a, b):
    """Fisher on crowd-by-78 (lower with an outsider?), pulled-in-hold (higher?), pulled-before-crowd (higher?)"""
    if not a or not b: return
    f1 = fisher(a["n"] - a["c78"], a["c78"], b["n"] - b["c78"], b["c78"]); f2 = fisher(a["pb"], a["n"] - a["pb"], b["pb"], b["n"] - b["pb"])
    f3 = fisher(a["pnc"], a["n"] - a["pnc"], b["pnc"], b["n"] - b["pnc"])
    print(f"    Fisher {lab}: no crowd by +78 one-sided p {f1[0]:.3g} (two-sided {f1[1]:.3g}); pulled<=sell {f2[0]:.3g} ({f2[1]:.3g}); pulled before crowd {f3[0]:.3g} ({f3[1]:.3g})")
def is_bot1(o): return o["w"].startswith(BOT1)
print(f"{len(P)} line pools, launches {utc(P[0]['ts'])} to {utc(P[-1]['ts'])} UTC; head {head['head']} {utc(head['head_ts'])}; stake {Q} ETH; buy at + 2, sell min(trigger + 20, + 80)")
print(f"pools with unknown-class swaps (tx not fetched, not a crowd recipient): {sum(1 for p in P if p['n_unknown'])}")
# exclude pools whose window ends (head) before + 300: too young to tell
P = [p for p in P if p["end"] >= 300 or (p["pull"] is not None and p["pull"] < 300)]
print(f"pools observed to + 300 or pulled: {len(P)}")
none = [p for p in P if not p["outs"]]
print("\n(a) any outside buyer >= 0.0005 ETH before the crowd's first real buy (or before the pull / + 3000 if no crowd)")
a0 = outcome("no outside buyer", none)
a1 = outcome("an outside buyer (any)", [p for p in P if p["outs"]])
a2 = outcome("an outside buyer that is not the +1 bot", [p for p in P if any(not is_bot1(o) for o in p["outs"])])
a3 = outcome("only the +1 bot", [p for p in P if p["outs"] and all(is_bot1(o) for o in p["outs"])])
cmp("any vs none", a1, a0); cmp("non-bot vs none", a2, a0); cmp("bot only vs none", a3, a0)
print("\n(b) an outside buyer whose first >= 0.0005 buy is in + 1..+ 10 (our landing zone is + 2)")
E = lambda p, f: [o for o in p["outs"] if 1 <= o["first_off"] <= 10 and f(o)]
b0 = outcome("no outside buyer at all before the crowd", none)
b1 = outcome("+1..+10 buyer (any)", [p for p in P if E(p, lambda o: True)])
b2 = outcome("+1..+10 buyer, not the +1 bot", [p for p in P if E(p, lambda o: not is_bot1(o))])
b3 = outcome("+1..+10 buyer not the bot, still holding at the crowd/pull", [p for p in P if E(p, lambda o: not is_bot1(o) and o["held_at_crowd"])])
b4 = outcome("+1..+10 buyer not the bot, sold before the crowd/pull", [p for p in P if E(p, lambda o: not is_bot1(o)) and not E(p, lambda o: not is_bot1(o) and o["held_at_crowd"])])
b5 = outcome("+1..+10 the +1 bot only", [p for p in P if E(p, is_bot1) and not E(p, lambda o: not is_bot1(o))])
b6 = outcome("+1..+10 the +1 bot only, holding at crowd", [p for p in P if E(p, lambda o: is_bot1(o) and o["held_at_crowd"]) and not E(p, lambda o: not is_bot1(o))])
cmp("+1..+10 any vs none", b1, b0); cmp("+1..+10 non-bot vs none", b2, b0); cmp("+1..+10 non-bot holding vs none", b3, b0); cmp("bot only vs none", b5, b0)
print("\n(c) by size of the biggest early (+1..+10) outside holder, not the bot")
for lo_, hi_ in ((0.0005, 0.001), (0.001, 0.003), (0.003, 0.01), (0.01, 100)):
    g = [p for p in P if any(lo_ <= o["first_eth"] < hi_ for o in E(p, lambda o: not is_bot1(o) and o["held_at_crowd"]))]
    r = outcome(f"holding, first buy {lo_}-{hi_} ETH", g); cmp(f"{lo_}-{hi_} vs none", r, b0)
print("\n(d) by period (launch day UTC): none / +1..+10 non-bot holders")
days = sorted({time.strftime('%m-%d', time.gmtime(p['ts'])) for p in P})
for d in days:
    g = [p for p in P if time.strftime('%m-%d', time.gmtime(p['ts'])) == d]
    print(f" {d}")
    x0 = outcome("none", [p for p in g if not p["outs"]]); x1 = outcome("+1..+10 non-bot holder", [p for p in g if E(p, lambda o: not is_bot1(o) and o["held_at_crowd"])]); cmp(d, x1, x0)
print("\n(e) by period: Oct 3-7 / Oct 8-12 (the task's window)")
for lab, lo_, hi_ in (("Oct 3-7", "10-03", "10-07"), ("Oct 8-12", "10-08", "10-12")):
    g = [p for p in P if lo_ <= time.strftime('%m-%d', time.gmtime(p['ts'])) <= hi_]
    print(f" {lab}")
    x0 = outcome("none", [p for p in g if not p["outs"]])
    x1 = outcome("+1..+10 non-bot holder", [p for p in g if E(p, lambda o: not is_bot1(o) and o["held_at_crowd"])]); cmp(lab + " non-bot", x1, x0)
    x2 = outcome("+1..+10 the +1 bot only", [p for p in g if E(p, is_bot1) and not E(p, lambda o: not is_bot1(o))]); cmp(lab + " bot", x2, x0)
    x3 = outcome("any non-bot buyer before the crowd", [p for p in g if any(not is_bot1(o) for o in p["outs"])]); cmp(lab + " any non-bot", x3, x0)
print("\n(g) the pull floor: pulls at or before + 80 (our cap), + 90, + 100, + 120 by group (an earlier floor would reach our sell)")
def floor(lab, ps, ref=None):
    n = len(ps); ks = [sum(1 for p in ps if p["pull"] is not None and p["pull"] <= c) for c in (80, 90, 100, 120)]
    line = f"  {lab:<44} n {n:>4}  " + "  ".join(f"<=+{c}: {k} ({k/max(1,n):.1%}, exact upper {cp_upper(k, n):.1%})" for c, k in zip((80, 90, 100, 120), ks))
    if ref:
        line += "  | Fisher vs none (higher): " + " ".join(f"{fisher(k, n - k, r, ref[1] - r)[0]:.3g}" for k, r in zip(ks, ref[0]))
    print(line); return ks, n
r0 = floor("no outside buyer before the crowd", none)
floor("the +1 bot at +1 (no other early buyer)", [p for p in P if E(p, is_bot1) and not E(p, lambda o: not is_bot1(o))], r0)
floor("+1..+10 non-bot buyer", [p for p in P if E(p, lambda o: not is_bot1(o))], r0)
floor("+1..+10 non-bot buyer >= 0.001 ETH", [p for p in P if E(p, lambda o: not is_bot1(o) and o["eth_pre"] >= 0.001)], r0)
floor("+1..+10 any outside buyer", [p for p in P if E(p, lambda o: True)], r0)
floor("all pools", P, r0)

print("\n(h) pools the crowd had not reached by + 100 (the operator's 'abort' branch): pulled by + 90 / + 100 / + 150, with an outside holder"
      " at + 80 (bought >= 0.0005 ETH by + 78 and still holding at + 80) or not")
def holds_at(p, t, f):
    return [o for o in p["outs"] if f(o) and o["first_off"] <= t - 2 and (o["exit_off"] is None or o["exit_off"] > t)]
nc = [p for p in P if (p["frb"] is None or p["frb"] > 100) and (p["end"] >= 150 or p["pull"] is not None)]
for lab, f in (("any outside holder", lambda o: True), ("non-bot holder", lambda o: not is_bot1(o)), ("the +1 bot", is_bot1),
               ("non-bot holder >= 0.001 ETH", lambda o: not is_bot1(o) and o["eth_pre"] >= 0.001),
               ("non-bot holder in since +1..+10", lambda o: not is_bot1(o) and o["first_off"] <= 10),
               ("non-bot holder >= 0.001 in since +1..+10", lambda o: not is_bot1(o) and o["first_off"] <= 10 and o["eth_pre"] >= 0.001)):
    a = [p for p in nc if holds_at(p, 80, f)]; b = [p for p in nc if not holds_at(p, 80, lambda o: True)]
    CS = (80, 83, 85, 90, 100, 150)
    ka = [sum(1 for p in a if p["pull"] is not None and p["pull"] <= c) for c in CS]; kb = [sum(1 for p in b if p["pull"] is not None and p["pull"] <= c) for c in CS]
    print(f"  {lab:<30} with {len(a):>4}: " + " ".join(f"<=+{c} {k} ({k/max(1,len(a)):.1%})" for c, k in zip(CS, ka))
          + f"  | no holder at all {len(b):>4}: " + " ".join(f"<=+{c} {k} ({k/max(1,len(b)):.1%})" for c, k in zip(CS, kb))
          + "  | Fisher one-sided " + " ".join(f"{fisher(x, len(a) - x, y, len(b) - y)[0]:.3g}" for x, y in zip(ka, kb)))

    # Cochran-Mantel-Haenszel across launch days, pulled <= + 100 and <= + 90 (holder vs no holder)
    import math
    for cut in (90, 100):
        num = var = 0.0; orn = ord_ = 0.0
        for d in sorted({time.strftime('%m-%d', time.gmtime(p['ts'])) for p in a + b}):
            A = [p for p in a if time.strftime('%m-%d', time.gmtime(p['ts'])) == d]; Bq = [p for p in b if time.strftime('%m-%d', time.gmtime(p['ts'])) == d]
            x = sum(1 for p in A if p["pull"] is not None and p["pull"] <= cut); y = sum(1 for p in Bq if p["pull"] is not None and p["pull"] <= cut)
            n1, n2 = len(A), len(Bq); N = n1 + n2; m1 = x + y
            if N < 2 or n1 == 0 or n2 == 0: continue
            num += x - n1 * m1 / N; var += n1 * n2 * m1 * (N - m1) / (N * N * (N - 1))
            orn += x * (n2 - y) / N; ord_ += y * (n1 - x) / N
        if var > 0:
            z = num / math.sqrt(var); pv = 0.5 * math.erfc(z / math.sqrt(2))
            print(f"      CMH by launch day, pulled <= +{cut}: z {z:.2f}, one-sided p {pv:.3g}, MH odds ratio {orn / ord_ if ord_ else float('inf'):.2f}")
    lags = sorted(p["pull"] - min(o["first_off"] for o in holds_at(p, 80, f)) for p in a if p["pull"] is not None and p["pull"] <= 100)
    if lags: print(f"      pulled <= +100: pull minus the holder's first buy {lags}")

print("\n(i) the same question without looking ahead: pools alive at + 78 with no crowd trigger by + 60 (our sell is the cap's), split by an outside"
      " holder at + 78; the pull and the crowd's first real buy in the next blocks")
at78 = [p for p in P if (p["pull"] is None or p["pull"] > 78) and (p["trig"] is None or p["trig"] > 60) and (p["end"] >= 200 or p["pull"] is not None)]
for lab, f in (("no outside holder", None), ("any outside holder", lambda o: True), ("non-bot holder", lambda o: not is_bot1(o)), ("the +1 bot only", "bot"),
               ("non-bot holder >= 0.001 ETH", lambda o: not is_bot1(o) and o["eth_pre"] >= 0.001), ("non-bot holder since +1..+10", lambda o: not is_bot1(o) and o["first_off"] <= 10)):
    if f is None: g = [p for p in at78 if not holds_at(p, 78, lambda o: True)]
    elif f == "bot": g = [p for p in at78 if holds_at(p, 78, is_bot1) and not holds_at(p, 78, lambda o: not is_bot1(o))]
    else: g = [p for p in at78 if holds_at(p, 78, f)]
    n = len(g)
    if not n: continue
    pk = [sum(1 for p in g if p["pull"] is not None and p["pull"] <= c and (p["frb"] is None or p["frb"] > p["pull"])) for c in (80, 83, 85, 90, 100, 150)]
    ck = [sum(1 for p in g if p["frb"] is not None and p["frb"] <= c) for c in (80, 100, 150)]
    print(f"  {lab:<30} n {n:>4}: pulled before any crowd by " + " ".join(f"+{c} {k} ({k/n:.1%}{', Wilson %.1f-%.1f%%' % tuple(100 * v for v in wilson(k, n)) if c in (90, 100) else ''})" for c, k in zip((80, 83, 85, 90, 100, 150), pk))
          + "; crowd by " + " ".join(f"+{c} {k/n:.0%}" for c, k in zip((80, 100, 150), ck)))

print("\n(j) (i) by period: pulled before any crowd by + 90 / + 100, no outside holder vs a non-bot holder at + 78")
hts = max(p["ts"] for p in P)
for lab, lo_ in (("Oct 3-7", 0), ("Oct 8-12", time.mktime((2026, 10, 8, 0, 0, 0, 0, 0, 0)) - time.timezone), ("last 48 h", hts - 48 * 3600), ("last 24 h", hts - 24 * 3600)):
    hi_ = time.mktime((2026, 10, 8, 0, 0, 0, 0, 0, 0)) - time.timezone if lab == "Oct 3-7" else 1e12
    g = [p for p in at78 if lo_ <= p["ts"] < hi_]
    a = [p for p in g if holds_at(p, 78, lambda o: not is_bot1(o))]; b = [p for p in g if not holds_at(p, 78, lambda o: True)]
    f = lambda q, c: sum(1 for p in q if p["pull"] is not None and p["pull"] <= c and (p["frb"] is None or p["frb"] > p["pull"]))
    print(f"  {lab:<10} holder {len(a):>4}: +90 {f(a, 90)} +100 {f(a, 100)} | none {len(b):>4}: +90 {f(b, 90)} +100 {f(b, 100)} | Fisher +100 one-sided {fisher(f(a, 100), len(a) - f(a, 100), f(b, 100), len(b) - f(b, 100))[0]:.3g}")

print("\n(k) (i) by the holder's route (the contract its buy called): pulled before any crowd by + 90 / + 100 / + 150")
routes = collections.Counter(o["to"] for p in at78 for o in holds_at(p, 78, lambda o: not is_bot1(o)))
for r, _ in routes.most_common(6):
    g = [p for p in at78 if holds_at(p, 78, lambda o, r=r: not is_bot1(o) and o["to"] == r)]
    f = lambda c: sum(1 for p in g if p["pull"] is not None and p["pull"] <= c and (p["frb"] is None or p["frb"] > p["pull"]))
    print(f"  via {r}: pools {len(g):>4}: +90 {f(90)} ({f(90)/len(g):.1%}) +100 {f(100)} ({f(100)/len(g):.1%}) +150 {f(150)} ({f(150)/len(g):.1%})")

print("\n(l) anchored on the launch or on the holder's buy? abort-branch pools (no crowd before the pull) pulled by + 150 with a non-bot holder at + 78:"
      " the pull offset by the earliest holder's entry")
rows_l = []
for p in at78:
    hs = holds_at(p, 78, lambda o: not is_bot1(o))
    if hs and p["pull"] is not None and p["pull"] <= 150 and (p["frb"] is None or p["frb"] > p["pull"]):
        rows_l.append((min(o["first_off"] for o in hs), p["pull"]))
for lo_, hi_ in ((1, 10), (11, 40), (41, 78)):
    g = [pl for e, pl in rows_l if lo_ <= e <= hi_]
    if g: print(f"  holder in since +{lo_}..+{hi_}: n {len(g):>3}  pull offset p10/50/90 {pct(g,.1)}/{pct(g,.5)}/{pct(g,.9)}  pull minus entry median {pct([pl - e for e, pl in rows_l if lo_ <= e <= hi_],.5)}")
if len(rows_l) > 2:
    xs = [e for e, _ in rows_l]; ys = [pl for _, pl in rows_l]; mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    print(f"  slope of the pull offset on the entry offset: {sxy / sxx:.2f} (1 = anchored on the buy, 0 = on the launch), n {len(xs)}")

print("\n(f) the closest analogs of our trade: a non-bot outside buy >= 0.0015 ETH landing at + 1..+ 5 (we land 0.002 ETH at + 2), every pool")
an = [(p, o) for p in P for o in p["outs"] if not is_bot1(o) and 1 <= o["first_off"] <= 5 and o["eth_pre"] >= 0.0015]
outcome("analog pools", sorted({p["pool"]: p for p, o in an}.values(), key=lambda p: p["lb"]))
for p, o in sorted(an, key=lambda r: r[0]["lb"]):
    print(f"   {utc(p['ts'])} {p['pool'][:10]} {o['w'][:10]} via {(o['to'] or '')[:10]} +{o['first_off']} {o['first_eth']:.4f} ETH; sold half at {o['exit_off']}; crowd +{p['frb']} wave {p['wave']:.3f};"
          f" pull +{p['pull']}; our sell +{p['sell']}; rule {p['ret']*100 if p['ret'] is not None else float('nan'):+.2f}%; it got back {o['eth_out']:.4f} of {o['eth_in']:.4f}")
json.dump([{k: v for k, v in p.items() if k not in ("ev", "sw")} for p in P], open(J("r05_groups.json"), "w"))
