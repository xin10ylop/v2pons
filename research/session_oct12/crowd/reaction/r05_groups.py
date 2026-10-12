"""(1) the crowd's and the operator's behaviour in pools where an outside wallet bought >= 0.0005 ETH before the crowd's first real buy,
against pools with no such buyer. Groups: by when the outsider bought (in our landing zone + 1..+ 10, or any time before the crowd),
whether it still held at the crowd's first real buy, and whether it is the recurring + 1 bot (0x776e5a2a) or anyone else. Outcomes: the
crowd came (before the pull, within + 3000), by + 78; its first real buy's offset; its wave (ETH bought in [frb, frb + 20]); the pull
before our sell (min(trigger + 20, + 80)), before the crowd; the rule's return at 0.002 ETH ($5) (analyst C's V3 replay, no reaction modelled)."""
from rlib import *
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
Q = float(os.environ.get("Q", "0.002"))     # $5 at ~$2,515 (r10_ethusd.out)
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
print("\n(f) the closest analogs of our trade: a non-bot outside buy >= 0.0015 ETH landing at + 1..+ 5 (we land 0.002 ETH at + 2), every pool")
an = [(p, o) for p in P for o in p["outs"] if not is_bot1(o) and 1 <= o["first_off"] <= 5 and o["eth_pre"] >= 0.0015]
outcome("analog pools", sorted({p["pool"]: p for p, o in an}.values(), key=lambda p: p["lb"]))
for p, o in sorted(an, key=lambda r: r[0]["lb"]):
    print(f"   {utc(p['ts'])} {p['pool'][:10]} {o['w'][:10]} via {(o['to'] or '')[:10]} +{o['first_off']} {o['first_eth']:.4f} ETH; sold half at {o['exit_off']}; crowd +{p['frb']} wave {p['wave']:.3f};"
          f" pull +{p['pull']}; our sell +{p['sell']}; rule {p['ret']*100 if p['ret'] is not None else float('nan'):+.2f}%; it got back {o['eth_out']:.4f} of {o['eth_in']:.4f}")
json.dump([{k: v for k, v in p.items() if k not in ("ev", "sw")} for p in P], open(J("r05_groups.json"), "w"))
