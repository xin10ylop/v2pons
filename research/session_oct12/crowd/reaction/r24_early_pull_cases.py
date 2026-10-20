"""every pool pulled at or before + 100: its outside buyers before the pull (wallet, offset, ETH, whether it still held at the pull), the
crowd's first real buy, the +1 bot; and the reverse view, per early non-bot outside buyer (+ 1..+ 10, >= 0.0005 ETH): when its pool was
pulled, as blocks after its buy."""
from rlib import *
P = load(); BOT1 = "0x776e5a2a"
ear = sorted([p for p in P if p["pull"] is not None and p["pull"] <= 100], key=lambda p: p["pull"])
print(f"{len(ear)} pools pulled at or before + 100 (of {len(P)})")
for p in ear:
    bot = any(o["w"].startswith(BOT1) for o in p["outs"])
    others = [o for o in p["outs"] if not o["w"].startswith(BOT1)]
    desc = "; ".join(f"{o['w'][:10]} via {(o['to'] or '')[:10]} +{o['first_off']} {o['eth_pre']:.4f} {'held' if o['held_at_crowd'] else 'sold@' + str(o['exit_off'])}" for o in others) or "none"
    print(f"  pull +{p['pull']:<4} {utc(p['ts'])} {p['pool'][:10]} crowd {p['frb']} bot {'yes' if bot else 'no '} | non-bot outsiders: {desc}")
print("\nearly non-bot outside buyers (first >= 0.0005 ETH buy at + 1..+ 10): pull minus its buy")
lag = []; lagh = []
for p in P:
    for o in p["outs"]:
        if o["w"].startswith(BOT1) or not 1 <= o["first_off"] <= 10: continue
        if p["pull"] is not None: lag.append(p["pull"] - o["first_off"]); (lagh.append(p["pull"] - o["first_off"]) if o["held_at_crowd"] else None)
print(f"  all: n {len(lag)} p5/10/25/50 {pct(lag,.05)}/{pct(lag,.1)}/{pct(lag,.25)}/{pct(lag,.5)}; within 78: {sum(1 for v in lag if v <= 78)}, within 88: {sum(1 for v in lag if v <= 88)}, within 98: {sum(1 for v in lag if v <= 98)}")
print(f"  still holding at the crowd/pull: n {len(lagh)} p5/10/25/50 {pct(lagh,.05)}/{pct(lagh,.1)}/{pct(lagh,.25)}/{pct(lagh,.5)}; within 78: {sum(1 for v in lagh if v <= 78)}, within 88: {sum(1 for v in lagh if v <= 88)}")
