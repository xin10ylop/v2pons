#!/usr/bin/env python3
"""linescan.py DUMP.json SEC_PER_BLOCK [MIN_POOLS]: every line in a buyerlab DUMP, screened for the one property that makes money -- a
one-off outsider can buy in without the line turning on them.

crowd    a wallet that buys in 3+ pools anywhere in the dump (an operator's fleet, a sniper, a regular): never an outsider here
outsider a wallet that buys (0.001 native+) in only 1-2 pools of the whole dump, not the pool's launcher
For every line (pools sharing a token-code template) with MIN_POOLS+ pools, over its pools where an outsider bought:
  fast pull   share pulled within 5 s of the outsider's first buy (the C-1 / operator A / Base timer defence)
  flow after  crowd native that came in AFTER the outsider's buy, against the crowd native after the same offset in the line's clean pools
              (a crowd that stops when someone is ahead shows a ratio near 0; a blind one near 1)
  exit        share of outsiders that sold 80%+ of their tokens before the pull, and their median return
and, for scale: pools a day, crowd native per pool, the median pull time of clean pools, the fee.
A tradeable line: no fast pull, flow after near or above 1, crowd native worth selling into. Read-only (the dump)."""
import sys, json, collections, statistics as st

D = json.load(open(sys.argv[1])); SPB = float(sys.argv[2]); MIN_POOLS = int(sys.argv[3]) if len(sys.argv) > 3 else 15
P = D["pools"]; FAST = max(1, int(5 / SPB))
days = max(1, len({p["bn"] // int(86400 / SPB) for p in P.values()}))
cnt = collections.Counter()
for p in P.values():
    for w in {s[3] for s in p.get("swaps", []) if s[1] > 0 and s[3] not in ("?", None)}:
        cnt[w] += 1
crowd = {w for w, n in cnt.items() if n >= 3}
lines = collections.defaultdict(list)
for pid, p in P.items():
    lines[tuple(p["grp"])].append(pid)
rows = []
for line, pids in lines.items():
    if len(pids) < MIN_POOLS:
        continue
    outp = []; clean = []
    for pid in pids:
        p = P[pid]; sw = sorted(p.get("swaps", [])); bn = p["bn"]; pull = p["pull"]
        cin = [(s[0] - bn, s[1]) for s in sw if s[3] in crowd and s[1] > 0 and s[3] != p["launcher"]]
        outs = [s for s in sw if s[1] >= 0.001 and s[3] not in crowd and s[3] not in ("?", None) and s[3] != p["launcher"]]
        if outs:
            o = outs[0]; w = o[3]; off = o[0] - bn
            bought = sum(s[2] for s in sw if s[3] == w and s[1] > 0); nin = sum(s[1] for s in sw if s[3] == w and s[1] > 0)
            sold = sum(-s[2] for s in sw if s[3] == w and s[1] < 0); nout = sum(-s[1] for s in sw if s[3] == w and s[1] < 0)
            outp.append({"off": off, "lag": (pull - o[0]) if pull is not None else None, "after": sum(v for t, v in cin if t > off),
                         "exit": bought > 0 and sold >= 0.8 * bought, "ret": (nout / nin - 1) if nin > 0 and bought > 0 and sold >= 0.8 * bought else None})
        else:
            clean.append({"cin": cin, "pull": (pull - bn) if pull is not None else None})
    crowd_eth = st.median([sum(v for _, v in c["cin"]) for c in clean]) if clean else 0.0
    r = {"line": line[1] if len(line) > 1 else line, "pools": len(pids), "per_day": len(pids) / days, "n_out": len(outp), "crowd_eth": crowd_eth,
         "clean_pull": st.median([c["pull"] for c in clean if c["pull"] is not None]) if any(c["pull"] is not None for c in clean) else None,
         "fee": st.median([P[x]["f"] for x in pids])}
    if outp:
        lags = [o["lag"] for o in outp if o["lag"] is not None]
        r["fast"] = sum(1 for l in lags if l <= FAST) / len(outp)
        ratios = []
        for o in outp:
            ref = [sum(v for t, v in c["cin"] if t > o["off"]) for c in clean]
            if ref and st.median(ref) > 0:
                ratios.append(o["after"] / st.median(ref))
        r["flow"] = st.median(ratios) if ratios else None
        r["exit"] = sum(1 for o in outp if o["exit"]) / len(outp)
        rets = [o["ret"] for o in outp if o["ret"] is not None]
        r["ret"] = st.median(rets) if rets else None
    rows.append(r)

def score(r):
    if r["n_out"] < 3:
        return -9
    return (1 - r.get("fast", 1)) + min(r.get("flow") or 0, 1.5) + r.get("exit", 0)
rows.sort(key=lambda r: -score(r))
f = lambda v, fmt: "-" if v is None else format(v, fmt)
print(f"{len(P)} pools, {len(crowd)} recurring wallets (crowd), {days} day(s); fast pull = within {FAST} blocks (5 s) of the outsider's buy")
print(f"{'line':26s} {'pools/d':>7s} {'crowd':>7s} {'fee':>6s} {'cleanPull':>9s} | {'outPools':>8s} {'fastPull':>8s} {'flowAfter':>9s} {'exit':>5s} {'exitRet':>7s}")
for r in rows:
    print(f"{str(r['line'])[:26]:26s} {r['per_day']:7.0f} {r['crowd_eth']:7.3f} {r['fee']:6.2%} {f(r['clean_pull'], 'g'):>9s} | {r['n_out']:8d} {f(r.get('fast'), '.0%'):>8s} {f(r.get('flow'), '.2f'):>9s} {f(r.get('exit'), '.0%'):>5s} {f(r.get('ret'), '+.0%'):>7s}")
