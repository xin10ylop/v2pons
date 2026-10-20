"""When does the bot sign its first buy? Its calldata carries a deadline = floor(sign time) + 1200 s (a07 finds 1198-1200 below ts(T)
+ 1200). Compare floor(sign time) with the block clock: by the position of T inside its second (from the timestamps of T-2..T+1),
the share of buys signed in the previous second gives the sign-to-land latency."""
import pickle, json, collections
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]
tx = {}
for l in open("txcache.jsonl"): x = json.loads(l); tx[x["hash"]] = x
B = {}
for l in open("blocks.jsonl"): x = json.loads(l); B[x["n"]] = x
word = lambda inp, i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
P = [p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None]
c = collections.defaultdict(collections.Counter)
for p in P:
    T = p["Tbn"]; ts = {k: B[T + k]["ts"] for k in (-2, -1, 0, 1)}
    if ts[-1] < ts[0]: k = "T is block 1 of its second"
    elif ts[-2] < ts[-1]: k = "T is block 2"
    else: k = "T is block >= 3"
    sign = word(tx[p["Ttx"]]["input"], 6) - 1200
    c[k][ts[0] - sign] += 1
for k in sorted(c): 
    n = sum(c[k].values()); print(f"{k}: n {n}; ts(T) - floor(sign time): {dict(sorted(c[k].items()))}; signed in the previous second {round(100 * (n - c[k][0]) / n)}%")
# 2nd buys for comparison (not first)
