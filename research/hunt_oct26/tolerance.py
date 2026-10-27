#!/usr/bin/env python3
"""tolerance.py CHAIN SHAPE DAY...: how big a buy from outside a line lets through before it pulls. The line is the pulled pools of the tapes
whose shape starts with SHAPE (e.g. "v4 fee 10000 ts 200") and whose native in is one of NIN (env, comma list; default all).

Buyers through the pool token's Transfer logs, as in pnlfast.py. Recurring buyers (in 3+ of a day's line pools: the line's own bots and the
dust snipers that ride it) are left out; every other buyer's first buy is a stranger buy. By the size of that buy: how many, how soon the pull
followed it, the share pulled within WIN seconds (env, default 5) against the line's base rate (the share of the line's pools still alive at
that buy's pool age that were pulled within the next WIN seconds), and the share that sold before the pull. Then the TOP (env, default 15)
recurring buyers: pools, buy size, how often they got out, net. Read-only, public RPCs."""
import os, sys, json, gzip, bisect, collections, statistics as st
import hlib as H

T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
WIN = float(os.environ.get("WIN", "5"))
NIN = {float(x) for x in os.environ["NIN"].split(",")} if os.environ.get("NIN") else None
TOP = int(os.environ.get("TOP", "15"))
BUCKETS = [0, 0.00003, 0.00006, 0.0001, 0.0002, 0.0005, 0.001, 0.01, 1e9]


def main(ch, shape, days):
    here = os.path.dirname(os.path.abspath(__file__))
    rows, lives = [], []
    reg = collections.defaultdict(list)                # recurring buyer -> [(bought, sold, got out, pull after its first buy)]
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")); bt = d["bt"]
        cen = {p["id"]: p for p in json.load(open(os.path.join(here, f"out/{ch}_{day}_00.json")))["chains"][ch]["rugs"]}
        pools = {pid: p for pid, p in d["pools"].items() if pid in cen and p["shape"].startswith(shape)
                 and (NIN is None or round(p["nin"] or 0, 2) in NIN)}
        if not pools:
            continue
        lives += [(p["pull"] - p["add"]) * bt for p in pools.values()]
        holder = {pid: (cen[pid]["pm"] if p["venue"] == "v4" else pid[3:]).lower() for pid, p in pools.items()}
        tok = {pid: cen[pid]["tok"].lower() for pid in pools}
        toks = sorted(set(tok.values())); n = 300 if ch == "rh" else 10
        xfer = collections.defaultdict(list)
        for i in range(0, len(toks), n):
            grp = set(toks[i:i + n]); ps = [p for pid, p in pools.items() if tok[pid] in grp]
            for x in H.logs(ch, min(p["bn"] for p in ps), max(p["pull"] for p in ps) + 2, [T], sorted(grp)):
                xfer[(x["transactionHash"], x["address"].lower())].append((H.a_of(x["topics"][1]), H.a_of(x["topics"][2])))
        flows = {}
        seen = collections.Counter()
        for pid, p in pools.items():
            pos = collections.defaultdict(lambda: [None, 0.0, 0.0])                # buyer -> [first buy (block, native), bought, sold]
            for e in p["ev"]:
                if e[0] > p["pull"]:
                    continue
                cp = next((t if e[2] > 0 else f for f, t in xfer.get((e[6], tok[pid]), []) if (e[2] > 0 and f == holder[pid]) or (e[2] < 0 and t == holder[pid])), None)
                if not cp or cp == p["frm"]:
                    continue
                x = pos[cp]
                if e[2] > 0:
                    x[1] += e[2]
                    if x[0] is None:
                        x[0] = (e[0], e[2])
                else:
                    x[2] += -e[2]
            flows[pid] = pos
            for cp, x in pos.items():
                if x[0]:
                    seen[cp] += 1
        for pid, pos in flows.items():
            p = pools[pid]
            for cp, (fb, bought, sold) in pos.items():
                if fb and seen[cp] >= 3:
                    reg[cp].append((bought, sold, sold > 0, (p["pull"] - fb[0]) * bt))
                if not fb or seen[cp] >= 3:
                    continue
                rows.append({"day": day, "pool": pid, "who": cp, "size": fb[1], "age": (fb[0] - p["add"]) * bt, "to_pull": (p["pull"] - fb[0]) * bt,
                             "out": sold > 0, "pnl": sold - bought})
        print(f"  {ch} {day}: {len(pools)} line pools, {sum(1 for r in rows if r['day'] == day)} stranger buys", flush=True)
    lives.sort()

    def base(age):                                     # share of the line's pools alive at this age that were pulled within WIN more seconds
        alive = len(lives) - bisect.bisect_right(lives, age)
        return (bisect.bisect_right(lives, age + WIN) - bisect.bisect_right(lives, age)) / alive if alive else 0.0

    print(f"{ch} '{shape}' {NIN or ''} {days[0]}..{days[-1]}: {len(lives)} pools, life median {st.median(lives):.0f}s; {len(rows)} stranger buys")
    for lo, hi in zip(BUCKETS, BUCKETS[1:]):
        rs = [r for r in rows if lo <= r["size"] < hi]
        if not rs:
            continue
        fast = sum(r["to_pull"] <= WIN for r in rs) / len(rs); exp = sum(base(r["age"]) for r in rs) / len(rs)
        print(f"  {lo:.5f}-{hi:<9g} buys {len(rs):4d} by {len({r['who'] for r in rs}):4d} | pull after a median {st.median(r['to_pull'] for r in rs):6.1f}s"
              f" | pulled within {WIN:g}s {fast:5.0%} (base rate {exp:4.0%}) | got out {sum(r['out'] for r in rs) / len(rs):4.0%}"
              f" | net {sum(r['pnl'] for r in rs):+.4f} on {sum(r['size'] for r in rs):.4f}", flush=True)
    print(f"  recurring buyers (3+ line pools a day), the {TOP} with the most pools:")
    for cp, xs in sorted(reg.items(), key=lambda kv: -len(kv[1]))[:TOP]:
        print(f"    {cp} pools {len(xs):5d} | buy median {st.median(x[0] for x in xs):.5f} | got out {sum(x[2] for x in xs) / len(xs):4.0%}"
              f" | net {sum(x[1] - x[0] for x in xs):+9.4f} | pull after its first buy, median {st.median(x[3] for x in xs):.0f}s")
    json.dump(rows, open(os.path.join(here, f"out/tolerance_{ch}_{shape.replace(' ', '_')}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
