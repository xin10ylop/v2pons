"""what a buy ahead of ours costs our entry: per pool, the tokens 0.0012 ETH buys at the head of + 2 (after every swap of blocks + 0..+ 1,
as we would land) against at the launch price (nobody ahead). The difference is the share of the trade's value lost to whoever bought
first (the + 1 bot's 0.001 ETH and anyone else at + 0..+ 1); a buyer landing in + 2 before us adds to it."""
from common import *
from wcommon import compact
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import V3Sim
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
Q = int(0.0012 * 1e18); rows = []
for line in open(J("r02_events_cache.jsonl")):
    e = json.loads(line); x = L[e["pool"]]; qs = x["qs"]; lb = x["lb"]
    ev = [c for c in (compact(l) for l in sorted(e["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))) if c]
    def tokens(upto, inclusive_block2=False):
        s = V3Sim(qs, 100)
        for c in ev:
            if c[1] - lb > upto or (c[1] - lb == upto and not inclusive_block2): break
            s.apply(c)
        return s.buy(Q) if s.ok() else None
    t0 = tokens(0, True)           # after the launch block (the mint), nobody else
    t2 = tokens(2)                 # head of + 2: after + 0..+ 1
    t2b = tokens(2, True)          # end of + 2: as if we landed last in + 2
    ah = sum((c[7] if qs == 0 else c[8]) for c in ev if c[0] == "s" and c[1] - lb <= 1 and (c[7] if qs == 0 else c[8]) > 0) / 1e18
    ah2 = sum((c[7] if qs == 0 else c[8]) for c in ev if c[0] == "s" and c[1] - lb == 2 and (c[7] if qs == 0 else c[8]) > 0) / 1e18
    if t0 and t2 and t2b: rows.append((ah, ah2, 1 - t2 / t0, 1 - t2b / t0))
print(f"{len(rows)} pools; ETH bought in + 0..+ 1: any in {sum(1 for r in rows if r[0] > 0)}; in + 2: {sum(1 for r in rows if r[1] > 0)}")
for lab, g in (("nobody ahead", [r for r in rows if r[0] == 0]), ("someone at + 0..+ 1", [r for r in rows if r[0] > 0])):
    c = [r[2] for r in g]; c2 = [r[3] for r in g]
    print(f"  {lab:<22} n {len(g):>4}: tokens lost at the head of + 2 p50 {pct(c,.5)*100:.2f}% p90 {pct(c,.9)*100:.2f}% max {max(c)*100:.2f}%; "
          f"landing last in + 2: p50 {pct(c2,.5)*100:.2f}% p90 {pct(c2,.9)*100:.2f}% max {max(c2)*100:.2f}%; ETH ahead p50 {pct([r[0] for r in g],.5):.5f}")
