#!/usr/bin/env python3
"""walletpnl.py DUMP.json[,DUMP.json...] [MIN_POOLS]: who actually makes money here? Rank every wallet by realized native across all pools.

The blunt test of "is anything tradeable": not "is there a 2.433-shaped line" but "is any wallet profitable as a trader". For each wallet,
over every pool in the dumps:
  in      native spent on buys
  out     native received on sells
  realized = out - in   (a wallet still holding tokens shows this as profit only if it sold; tokens left unsold are listed separately)
  left    tokens still held at the end of the window (unrealized; a honeypot victim shows big `in`, `out` ~0, `left` > 0)
Each wallet: pools traded, realized native, the share of its pools where it got >=80% of its tokens back out (a real exit), and whether it
is a known operator router / launcher (tagged, and excluded from the ranking). A wallet with many pools, positive realized native and a high
exit share is a trader to copy. If the top of the list is only operator fleets and everyone else is net negative, the market is shut to
outsiders. Read-only (the dumps)."""
import sys, json, collections, statistics as st

DUMPS = sys.argv[1].split(","); MIN_POOLS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
PUBLIC = {"0x8876789976decbfcbbbe364623c63652db8c0904", "0xcaf681a66d020601342297493863e78c959e5cb2", "0x89e5db8b5aa49aa85ac63f691524311aeb64ed43",
          "0x6ff5693b99212da76ad316178a184ab56d299b43", "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x2626664c2603336e57b271c5c0b26f421741e481",
          "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0x1cbaf24d53fe930fce8eff149fa797d2611da149"}
pools = {}
for f in DUMPS:
    pools.update(json.load(open(f))["pools"])
# a wallet that launches 1+ pools here is an operator, not a trader
launchers = {p["launcher"] for p in pools.values() if p.get("launcher")}
W = collections.defaultdict(lambda: {"in": 0.0, "out": 0.0, "tin": 0.0, "tout": 0.0, "pools": set(), "exits": 0})
perpool = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0]))  # pool -> wallet -> [nin,nout,tbuy,tsell]
for pid, p in pools.items():
    for blk, nat, tok, w in p.get("swaps", []):
        if w in ("?", None):
            continue
        a = perpool[pid][w]
        if nat > 0:
            a[0] += nat; a[2] += tok
        else:
            a[1] += -nat; a[3] += -tok
for pid, ws in perpool.items():
    for w, (nin, nout, tb, ts) in ws.items():
        if nin <= 0 and nout <= 0:
            continue
        d = W[w]; d["in"] += nin; d["out"] += nout; d["pools"].add(pid)
        if tb > 0 and ts >= 0.8 * tb:
            d["exits"] += 1
rows = []
for w, d in W.items():
    if len(d["pools"]) < MIN_POOLS:
        continue
    rows.append({"w": w, "pools": len(d["pools"]), "realized": d["out"] - d["in"], "in": d["in"], "out": d["out"],
                 "exit_share": d["exits"] / len(d["pools"]), "tag": "LAUNCHER" if w in launchers else ("ROUTER" if w in PUBLIC else "")})
traders = [r for r in rows if not r["tag"]]
traders.sort(key=lambda r: -r["realized"])
print(f"{len(pools)} pools; {len(rows)} wallets in {MIN_POOLS}+ pools ({sum(1 for r in rows if r['tag'])} tagged operator/router)")
print(f"\n== top 25 by realized native (operators/routers excluded) ==")
print(f"{'wallet':44s} {'pools':>5s} {'realized':>10s} {'spent':>9s} {'got':>9s} {'exit%':>5s}")
for r in traders[:25]:
    print(f"{r['w']:44s} {r['pools']:5d} {r['realized']:+10.3f} {r['in']:9.3f} {r['out']:9.3f} {r['exit_share']:5.0%}")
pos = [r for r in traders if r["realized"] > 0.01]
print(f"\ntraders (5+ pools, not operator/router): {len(traders)}; net positive realized: {len(pos)}; "
      f"net positive AND exit share >=50%: {sum(1 for r in pos if r['exit_share'] >= 0.5)}")
print(f"median realized across traders: {st.median([r['realized'] for r in traders]):+.4f} native")
print(f"\n== for reference, top 5 tagged operator/router wallets ==")
for r in sorted([r for r in rows if r['tag']], key=lambda r: -r['realized'])[:5]:
    print(f"{r['w']:44s} {r['pools']:5d} {r['realized']:+10.3f} {r['in']:9.3f} {r['out']:9.3f} {r['exit_share']:5.0%}  {r['tag']}")
