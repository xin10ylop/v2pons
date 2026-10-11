"""Global cadence and wall-clock tests on the full bot-buy stream (every PM->bot-router transfer, all lines, all pools, 10 h):
 - gaps between consecutive bot buys anywhere vs a geometric law with the same mean (a fixed global cadence or a queue would spike);
 - block number mod P and timestamp mod P (P 2..60) uniformity of the bot's buys (a ticker would concentrate them);
 - T's launch-side clock: T - L against L's second (ts mod 60), against L being the first block of its second, and T's own position."""
import pickle, json, collections, math
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; acts = D["acts"]
B = {}
for l in open("blocks.jsonl"): x = json.loads(l); B[x["n"]] = x
bn = [a["bn"] for a in acts]
g = [b - a for a, b in zip(bn, bn[1:])]
m = sum(g) / len(g); q = 1 / (m + 1)
print(f"global bot actions {len(bn)}, mean gap {m:.2f} blocks")
print("gap: observed vs geometric expectation (gap 0..30):")
print("  obs", [sum(1 for x in g if x == k) for k in range(31)])
print("  geo", [round(len(g) * q * (1 - q) ** k) for k in range(31)])
def chi(vals, P):
    c = collections.Counter(v % P for v in vals); e = len(vals) / P
    return sum((c[k] - e) ** 2 / e for k in range(P)), P - 1
worst = []
for P in range(2, 61):
    x, df = chi(bn, P); z = (x - df) / math.sqrt(2 * df); worst.append((z, P))
worst.sort(reverse=True)
print("block-number mod P of all bot buys, largest chi-square z over P=2..60:", [(P, round(z, 1)) for z, P in worst[:5]])
# T's phase by P (first buys only), 3.0/5.0
PP = [p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None]
Tabs = [p["Tbn"] for p in PP]
worst = []
for P in range(2, 31):
    x, df = chi(Tabs, P); worst.append(((x - df) / math.sqrt(2 * df), P))
worst.sort(reverse=True)
print("3.0/5.0 T block mod P, largest chi-square z over P=2..30:", [(P, round(z, 1)) for z, P in worst[:5]])
off = [p["Tbn"] - p["L"] for p in PP]
worst = []
for P in range(2, 31):
    x, df = chi(off, P); worst.append(((x - df) / math.sqrt(2 * df), P))
worst.sort(reverse=True)
print("3.0/5.0 (T - L) mod P, largest chi-square z over P=2..30:", [(P, round(z, 1)) for z, P in worst[:5]])
# L's second phase
for name, f in (("L first block of its second", lambda p: B[p["L"]]["ts"] > B[p["L"] - 1]["ts"]), ("L not first", lambda p: B[p["L"]]["ts"] == B[p["L"] - 1]["ts"])):
    v = sorted(p["T"] for p in PP if f(p)); print(f"{name}: n {len(v)} T p10/50/90 {v[len(v)//10]}/{v[len(v)//2]}/{v[9*len(v)//10]}")
for lo in range(0, 60, 15):
    v = sorted(p["T"] for p in PP if lo <= B[p["L"]]["ts"] % 60 < lo + 15); print(f"L at second {lo}-{lo+14} of its minute: n {len(v)} T p10/50/90 {v[len(v)//10]}/{v[len(v)//2]}/{v[9*len(v)//10]}")
v = sorted(off); n = len(v)
print("T - L (3.0+5.0) full distribution:", sorted(collections.Counter(v).items()))
print(f"  share in 27..57: {sum(1 for x in v if 27 <= x <= 57) / n:.0%}; max share of any 3 consecutive offsets (the best constant +-1 predictor): "
      f"{max(sum(1 for x in v if c - 1 <= x <= c + 1) for c in range(15, 65)) / n:.1%}")
