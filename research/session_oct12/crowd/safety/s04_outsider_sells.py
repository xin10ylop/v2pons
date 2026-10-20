"""Outsiders' real sells of the line's tokens, from the reaction check's per-pool records (../reaction/r04_pools_cache.jsonl, read only: every
Swap up to the pull with its transaction's sender and call; class 'other' = neither the crowd nor the launch wallet), restricted to this
check's launches (Oct 10 00:00 UTC on, s01). A sell = the token paid into the pool (WETH out). Per template (s02): outside sells, wallets,
routes, the offsets from the launch, sells after + 78 (our sell's window) and before the pull; outside positions (tx.from per pool) closed
(>= 95% of the tokens bought sold) and their realized return; the early buyers (first buy + 1..+ 5) who sold near + 80 (our trade's shape).
Writes s04_outsider_sells.out."""
from common import *
import collections, statistics as st
L = {x["pool"]: x for x in json.load(open(J("s01_launches.json")))["launches"]}
R = {r["pool"]: r for r in json.load(open(J("s02_codes.json")))}
P = []
for line in open(os.path.join(HERE, "..", "reaction", "r04_pools_cache.jsonl")):
    p = json.loads(line)
    if p["pool"] in L: P.append(p)
print(f"pools of this check {len(L)}; in the reaction records {len(P)} (its launches end {utc(max(p['ts'] for p in P))})")
TPL = {1764: "1764 B (census)", 5048: "5048 B (OZ ERC20)", 3854: "3854 B (ERC20Burnable, new)"}
by = collections.defaultdict(lambda: collections.Counter()); routes = collections.Counter(); offs = []; late = []; per_tpl_wallets = collections.defaultdict(set)
pos = []
for p in P:
    tpl = TPL[R[p["pool"]]["size"]]; pull = p["pull_off"]
    W = collections.defaultdict(lambda: {"in": 0, "out": 0, "tb": 0, "ts": 0, "fb": None, "ls": None, "to": collections.Counter()})
    for s in p["sw"]:
        if s["k"] != "other": continue
        w = W[s["from"]]; w["to"][(s["to"] or "")[:10] + ":" + (s["sel"] or "")] += 1
        if s["dq"] > 0:
            w["in"] += s["dq"]; w["tb"] += -s["dt"]; w["fb"] = s["off"] if w["fb"] is None else w["fb"]
        else:
            w["out"] += -s["dq"]; w["ts"] += s["dt"]; w["ls"] = s["off"]
            by[tpl]["sells"] += 1; routes[(s["to"] or "")[:10] + ":" + (s["sel"] or "") + f"/{s['len']}"] += 1; offs.append(s["off"]); per_tpl_wallets[tpl].add(s["from"])
            if s["off"] >= 78 and (pull is None or s["off"] < pull): late.append((p["pool"], s["off"], pull, s["from"], -s["dq"] / 1e18))
    for a, w in W.items():
        if w["tb"] == 0: continue
        closed = w["ts"] >= 0.95 * w["tb"]
        pos.append({"pool": p["pool"], "tpl": tpl, "w": a, "in": w["in"] / 1e18, "out": w["out"] / 1e18, "closed": closed, "fb": w["fb"], "ls": w["ls"], "pull": pull,
                    "ret": (w["out"] * w["tb"] / max(w["ts"], 1) / w["in"] - 1) if closed and w["in"] else None, "route": w["to"].most_common(1)[0][0]})
    by[tpl]["pools"] += 1
    if any(s["k"] == "other" and s["dq"] < 0 for s in p["sw"]): by[tpl]["pools with an outside sell"] += 1
for tpl, c in by.items():
    print(f"{tpl}: {dict(c)}; distinct outside sellers {len(per_tpl_wallets[tpl])}")
print(f"outside sells {len(offs)}; offset from the launch p10/50/90 {pct(offs, .1):.0f}/{pct(offs, .5):.0f}/{pct(offs, .9):.0f}; at +60..+120: {sum(60 <= o <= 120 for o in offs)}")
print("routes (to:selector/bytes):", routes.most_common(10))
print(f"outside sells at or after + 78 and before the pull: {len(late)} in {len(set(x[0] for x in late))} pools; ETH out p50 {pct([x[4] for x in late], .5):.5f}")
cl = [q for q in pos if q["closed"]]
print(f"\noutside positions {len(pos)} (wallet x pool); closed (>= 95% sold) {len(cl)}; realized return p10/50/90 {pct([q['ret'] for q in cl], .1):+.2%}/{pct([q['ret'] for q in cl], .5):+.2%}/{pct([q['ret'] for q in cl], .9):+.2%}; "
      f"> 0: {sum(q['ret'] > 0 for q in cl)}")
for tpl in TPL.values():
    c2 = [q for q in cl if q["tpl"] == tpl]
    if c2: print(f"   {tpl}: closed {len(c2)}, wallets {len(set(q['w'] for q in c2))}, realized p50 {pct([q['ret'] for q in c2], .5):+.2%}, > 0 {sum(q['ret'] > 0 for q in c2)}")
like = [q for q in cl if q["fb"] is not None and 1 <= q["fb"] <= 5 and q["ls"] is not None and 60 <= q["ls"] <= 130 and (q["pull"] is None or q["ls"] < q["pull"])]
print(f"\nour trade's shape (an outside first buy at + 1..+ 5, fully sold by + 60..+ 130, before the pull): {len(like)} positions, {len(set(q['w'] for q in like))} wallets; "
      f"realized p50 {pct([q['ret'] for q in like], .5) if like else 0:+.2%}, mean {st.mean([q['ret'] for q in like]) if like else 0:+.2%}")
for q in like[:12]:
    print(f"   {q['pool'][:10]} {q['tpl'][:4]} {q['w'][:10]} via {q['route']:<22} in {q['in']:.5f} out {q['out']:.5f} first buy +{q['fb']} last sell +{q['ls']} pull {q['pull']} ret {q['ret']:+.2%}")
op = [q for q in pos if not q["closed"] and q["pull"] is not None and (q["ls"] is None or q["ls"] < q["pull"])]
print(f"\noutside positions still holding at the pull: {len(op)} ({sum(q['ls'] is None for q in op)} never sold); ETH in {sum(q['in'] for q in op):.4f}")
