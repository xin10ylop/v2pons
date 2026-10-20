"""logs only: the wave and the pull in pools with the + 1 bot against the rest. Wave = ETH of every buy in [frb, frb + 20] (frb = the first
buy >= 0.005 ETH); total = ETH of every buy (not the bot's) before the pull or + 3000; the pull after the last buy >= 0.005 ETH; per launch
day and pooled, with Mann-Whitney p-values."""
from common import *
import collections
from wcommon import compact
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
R = []
for line in open(J("r02_events_cache.jsonl")):
    e = json.loads(line); x = L[e["pool"]]; lb = x["lb"]; qs = x["qs"]
    ev = sorted([c for c in (compact(l) for l in e["logs"]) if c], key=lambda c: (c[1], c[3]))
    bot = any(c[0] == "s" and c[5].startswith("0x570759db") and c[1] - lb <= 2 for c in ev)
    pl = [c[1] - lb for c in ev if c[0] == "b" and c[8] > 0]
    if not pl: pl = [c[1] - lb for c in (compact(l) for l in (B.get(x["pool"]) or {}).get("burns", [])) if c and c[8] > 0]
    pull = min(pl) if pl else None
    buys = [(c[1] - lb, (c[7] if qs == 0 else c[8]) / 1e18) for c in ev if c[0] == "s" and (c[7] if qs == 0 else c[8]) > 0 and not c[5].startswith("0x570759db")
            and (pull is None or c[1] - lb < pull)]
    big = [o for o, q in buys if q >= 0.005]
    frb = big[0] if big else None
    wave = sum(q for o, q in buys if frb is not None and frb <= o <= frb + 20)
    R.append({"bot": bot, "day": time.strftime("%m-%d", time.gmtime(x["ts"])), "frb": frb, "wave": wave, "tot": sum(q for o, q in buys), "nb": len(buys),
              "pull": pull, "after_last": (pull - big[-1]) if (pull is not None and big) else None, "last": big[-1] if big else None})
def row(lab, g):
    w = [z["wave"] for z in g if z["frb"] is not None]; t = [z["tot"] for z in g]; al = [z["after_last"] for z in g if z["after_last"] is not None]
    ls = [z["last"] - z["frb"] for z in g if z["last"] is not None]
    return w, t, al, ls, f"  {lab:<7} n {len(g):>4}: wave med {pct(w,.5):.3f} mean {sum(w)/max(1,len(w)):.3f}; total buys ETH med {pct(t,.5):.3f} mean {sum(t)/len(t):.3f}; " \
        f"buying span (last - first real buy) med {pct(ls,.5)}; pull - last real buy med {pct(al,.5)} p10 {pct(al,.1)}"
a = row("bot", [z for z in R if z["bot"]]); b = row("no bot", [z for z in R if not z["bot"]])
print(a[4]); print(b[4])
for i, nm in enumerate(("wave", "total", "pull - last real buy", "buying span")):
    print(f"   Mann-Whitney {nm}: p {mwu(a[i], b[i])[1]:.3g}")
for d in sorted({z["day"] for z in R}):
    print(d); print(row("bot", [z for z in R if z["bot"] and z["day"] == d])[4]); print(row("no bot", [z for z in R if not z["bot"] and z["day"] == d])[4])
