#!/usr/bin/env python3
"""Summaries of replay.py output: python3 analyze.py res.pkl [stake]"""
import sys, pickle, collections, statistics as st, time, json

P = [p for p in pickle.load(open(sys.argv[1], "rb")) if not p.get("skip")]
STAKE = sys.argv[2] if len(sys.argv) > 2 else "0.0012"


def agg(rs):
    v = [r["ret"] for r in rs if r and r.get("ret") is not None]
    if not v: return None
    ex = collections.Counter(r["exit"] for r in rs if r)
    return {"n": len(v), "mean": st.mean(v), "median": st.median(v), "pos": sum(1 for x in v if x > 0), "worst": min(v),
            "reverts": ex.get("buy_reverted", 0), "pulled": ex.get("pulled", 0) + ex.get("pull_before_buy", 0), "tp": ex.get("tp", 0),
            "skipped": sum(1 for r in rs if r is None or r.get("ret") is None), "bot_rev": sum(1 for r in rs if r and r.get("bot_reverts"))}


def key_pools(key):
    return [p["R"].get(key) for p in P]


def bucket(p):
    t = p["ts0"]; g = time.gmtime(t)
    return time.strftime("%m-%d ", g) + "%02d-%02dh" % (g.tm_hour // 6 * 6, g.tm_hour // 6 * 6 + 6)


if __name__ == "__main__":
    keys = sorted({k for p in P for k in p["R"]})
    rows = []
    for k in keys:
        parts = k.split("|")
        if parts[1] != STAKE: continue
        a = agg(key_pools(k))
        if a: rows.append((k, a))
    print(f"{len(P)} pools, stake {STAKE}")
    print("== main grid (view sells, stale 15, sell at head), sorted by mean; top 25")
    main = [(k, a) for k, a in rows if len(k.split("|")) == 6]
    for k, a in sorted(main, key=lambda x: -x[1]["mean"])[:25]:
        print(f"  {k:34s} n {a['n']:3d} mean {100*a['mean']:+6.2f}% med {100*a['median']:+6.2f}% pos {a['pos']:3d} worst {100*a['worst']:+7.1f}% rev {a['reverts']:2d} pull {a['pulled']:2d} tp {a['tp']:3d} botrev {a['bot_rev']}")
    print("== ideal")
    for k, a in rows:
        if k.endswith("ideal"):
            print(f"  {k:34s} n {a['n']:3d} mean {100*a['mean']:+6.2f}% med {100*a['median']:+6.2f}% pos {a['pos']:3d} worst {100*a['worst']:+7.1f}% rev {a['reverts']:2d} pull {a['pulled']:2d} botrev {a['bot_rev']}")
    print("== latency-averaged (b1/b2 x s1/s2) per entry/tp/D")
    grp = collections.defaultdict(list)
    for k, a in main:
        e, s, b, tp, D, sl = k.split("|"); grp[(e, tp, D)].append(a)
    lat = sorted(((g, st.mean(x["mean"] for x in v), min(x["mean"] for x in v), sum(x["pulled"] for x in v), sum(x["reverts"] for x in v)) for g, v in grp.items()), key=lambda r: -r[1])
    for g, m, w, pu, rv in lat[:20]:
        print(f"  {'|'.join(g):24s} mean over 4 latencies {100*m:+6.2f}% worst latency {100*w:+6.2f}% pulls {pu} reverts {rv}")
