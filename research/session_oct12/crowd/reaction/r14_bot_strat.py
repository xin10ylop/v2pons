"""the + 1 bot as a natural experiment (logs only): it buys ~0.001 ETH at + 1 in most line pools and almost never sells there, so its pools
carry an outside holder from + 1 on. Pull hazard (first Burn) per pool-block, bot pools against the rest, by age band, stratified by
launch day and launch variant (top tick): Mantel-Haenszel rate ratio with a Greenland-Robins 95% CI. Also the hazard of the first buy
>= 0.005 ETH (the crowd's, mostly). Age bands are pool age in blocks; the risk set ends at the event or at the observed window."""
from common import *
import collections, math
from wcommon import compact
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
head = json.load(open(J("r01_meta.json")))["head"]
BANDS = [(1, 40), (40, 80), (80, 120), (120, 200), (200, 400), (400, 800), (800, 1600), (1600, 3001)]
R = []
for line in open(J("r02_events_cache.jsonl")):
    e = json.loads(line); x = L[e["pool"]]; lb = x["lb"]; qs = x["qs"]
    ev = [c for c in (compact(l) for l in e["logs"]) if c]
    bot = any(c[0] == "s" and c[5].startswith("0x570759db") and c[1] - lb <= 2 for c in ev)
    pl = [c[1] - lb for c in ev if c[0] == "b" and c[8] > 0]
    if not pl:
        pl = [c[1] - lb for c in (compact(l) for l in (B.get(x["pool"]) or {}).get("burns", [])) if c and c[8] > 0]
    pull = min(pl) if pl else None
    frb = min([c[1] - lb for c in ev if c[0] == "s" and (c[7] if qs == 0 else c[8]) >= 5e15] or [None], key=lambda v: 1e18 if v is None else v)
    R.append({"bot": bot, "pull": pull, "frb": frb, "obs": min(3000, head - lb), "day": time.strftime("%m-%d", time.gmtime(x["ts"])), "var": x["hi"]})
def mh(event, start_after=None, lab=""):
    """event(z) -> offset or None; the at-risk time per pool runs from band start to min(event, obs)"""
    S = collections.defaultdict(lambda: [0, 0, 0, 0])      # stratum -> [e0, e1, d0, d1]
    bandtab = collections.defaultdict(lambda: [0, 0, 0, 0])
    for z in R:
        ev_ = event(z); stop = min(ev_ if ev_ is not None else 10 ** 9, z["obs"])
        for b in BANDS:
            lo, hi = b
            if stop < lo: break
            expo = min(stop, hi - 1) - lo + 1
            d = 1 if ev_ is not None and lo <= ev_ < hi and ev_ <= z["obs"] else 0
            k = (z["day"], z["var"], b); h = 1 if z["bot"] else 0
            S[k][h] += expo; S[k][2 + h] += d; bandtab[b][h] += expo; bandtab[b][2 + h] += d
    num = den = vs = 0.0
    for k, (e0, e1, d0, d1) in S.items():
        T = e0 + e1
        if not e0 or not e1: continue
        num += d1 * e0 / T; den += d0 * e1 / T; vs += (d0 + d1) * e1 * e0 / T ** 2
    rr = num / den; se = math.sqrt(vs / (num * den))
    print(f"\n{lab}: MH rate ratio bot / no bot, strata day x variant x age band: {rr:.2f} (95% CI {rr*math.exp(-1.96*se):.2f}-{rr*math.exp(1.96*se):.2f})")
    for b in BANDS:
        e0, e1, d0, d1 = bandtab[b]
        print(f"   age {str(b):>12}: no bot {d0:>4} events / {e0:>8} blocks = {1000*d0/max(1,e0):.3f}/1k   bot {d1:>4} / {e1:>8} = {1000*d1/max(1,e1):.3f}/1k   crude ratio {(d1/max(1,e1))/(d0/e0) if d0 else float('nan'):.2f}")
print(f"{len(R)} pools, bot in {sum(z['bot'] for z in R)}")
mh(lambda z: z["pull"], lab="pull (first Burn), any time")
mh(lambda z: z["pull"] if z["pull"] is not None and (z["frb"] is None or z["frb"] > z["pull"]) else None, lab="pull before any buy >= 0.005 ETH (censored at that buy)")
mh(lambda z: z["frb"] if z["frb"] is not None and (z["pull"] is None or z["pull"] > z["frb"]) else None, lab="first buy >= 0.005 ETH (the crowd's, mostly), before the pull")
