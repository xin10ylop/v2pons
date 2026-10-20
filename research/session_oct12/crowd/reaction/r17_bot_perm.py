"""logs only: a stratified permutation test of the + 1 bot's effect (labels shuffled within launch day x launch variant), 20,000 draws:
pulled by + 150, pulled by + 120, pulled within 20 blocks after the first buy >= 0.005 ETH (our exit window), the total buying before the
pull (log ETH), and the first-real-buy offset. Two-sided p = share of draws with |difference| >= the observed."""
from common import *
import collections, random, math
from wcommon import compact
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
R = []
for e in jl(J("r02_events_cache.jsonl")):
    x = L.get(e["pool"])
    if not x: continue
    lb = x["lb"]; qs = x["qs"]
    ev = sorted([c for c in (compact(l) for l in e["logs"]) if c], key=lambda c: (c[1], c[3]))
    bot = any(c[0] == "s" and c[5].startswith("0x570759db") and c[1] - lb <= 2 for c in ev)
    pl = [c[1] - lb for c in ev if c[0] == "b" and c[8] > 0]
    if not pl: pl = [c[1] - lb for c in (compact(l) for l in (B.get(x["pool"]) or {}).get("burns", [])) if c and c[8] > 0]
    pull = min(pl) if pl else 10 ** 9
    buys = [(c[1] - lb, (c[7] if qs == 0 else c[8]) / 1e18) for c in ev if c[0] == "s" and (c[7] if qs == 0 else c[8]) > 0 and not c[5].startswith("0x570759db") and c[1] - lb < pull]
    big = [o for o, q in buys if q >= 0.005]; f = big[0] if big else None
    R.append({"s": (time.strftime("%m-%d", time.gmtime(x["ts"])), x["hi"]), "bot": bot,
              "y": {"pulled<=150": float(pull <= 150), "pulled<=120": float(pull <= 120), "pull<=frb+20": float(f is not None and pull <= f + 20),
                    "log total buys": math.log(1e-4 + sum(q for o, q in buys)), "frb offset (if any)": f}})
strata = collections.defaultdict(list)
for i, z in enumerate(R): strata[z["s"]].append(i)
def diff(lbl, key):
    a = [R[i]["y"][key] for i in range(len(R)) if lbl[i] and R[i]["y"][key] is not None]; b = [R[i]["y"][key] for i in range(len(R)) if not lbl[i] and R[i]["y"][key] is not None]
    return sum(a) / len(a) - sum(b) / len(b), sum(a) / len(a), sum(b) / len(b)
obs = [z["bot"] for z in R]; rnd = random.Random(7); keys = list(R[0]["y"])
res = {k: diff(obs, k) for k in keys}; cnt = {k: 0 for k in keys}; N = 20000
for _ in range(N):
    lbl = obs[:]
    for idx in strata.values():
        v = [obs[i] for i in idx]; rnd.shuffle(v)
        for i, b in zip(idx, v): lbl[i] = b
    for k in keys:
        if abs(diff(lbl, k)[0]) >= abs(res[k][0]) - 1e-12: cnt[k] += 1
print(f"{len(R)} pools, bot {sum(obs)}; strata {len(strata)}; {N} within-stratum permutations")
for k in keys:
    d, a, b = res[k]
    print(f"  {k:<22} bot {a:.4f}  no bot {b:.4f}  difference {d:+.4f}  permutation p {cnt[k] / N:.4f}")
