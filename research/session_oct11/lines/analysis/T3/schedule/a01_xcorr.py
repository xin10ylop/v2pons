"""Cross-correlation of the 3.0 (and 5.0) first bot buy T (absolute block) against every other visible bot-side event:
other pools' bot buys/pulls, launches of every line, the pre-launch token distribution txs (bot router -> ~100-220 holders, L-10..-12),
the sentinel's dust buy, the pair partner's L and T. For each event class: histogram of (T - event block) over lags 1..60, against the
flat expectation from the event rate; a stable lead of 1-4 blocks would show as a spike at that lag."""
import pickle, json, collections, bisect
D = pickle.load(open("cache/data.pkl", "rb")); acts = D["acts"]; pools = D["pools"]
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
pmtx = set(a["tx"] for a in acts)
dist = {}
for l in open("cache/logs/bot2any.jsonl"):
    x = json.loads(l)
    if x["tx"] not in pmtx: dist.setdefault(x["tx"], x["bn"])
dist_bn = sorted(dist.values())
launch_bn = sorted(p["L"] for p in pools)
def lagh(Tabs, evs, lo=1, hi=60, exclude=None):
    evs = sorted(evs); h = collections.Counter()
    for i, T in enumerate(Tabs):
        a = bisect.bisect_left(evs, T - hi); b = bisect.bisect_right(evs, T - lo)
        for e in evs[a:b]: h[T - e] += 1
    return h
def show(name, h, n_T, rate, lo=1, hi=60):
    exp = n_T * rate
    row = " ".join(f"{h.get(k, 0)}" for k in range(lo, hi + 1))
    mx = max(range(lo, hi + 1), key=lambda k: h.get(k, 0))
    print(f"{name}: expected per lag {exp:.1f}; max at lag {mx} ({h.get(mx, 0)}); lags {lo}..{hi}: {row}")
blocks = D["meta"]["head"] - D["meta"]["start"]
for line in ("3.0", "5.0", "2.433"):
    P = [p for p in pools if p["line"] == line and p["T"] is not None]
    Tabs = [p["Tbn"] for p in P]
    own = set(p["token"] for p in P)
    print(f"\n=== {line}: {len(P)} pools with T")
    for kind in ("buy", "pull", "?"):
        evs = [a["bn"] for a in acts if a["kind"] == kind]
        # exclude the pool's own actions
        h = collections.Counter()
        for p in P:
            ev = [a["bn"] for a in acts if a["kind"] == kind and a["token"] != p["token"] and p["Tbn"] - 60 <= a["bn"] < p["Tbn"]]
            for e in ev: h[p["Tbn"] - e] += 1
        show(f"other pools' bot {kind}", h, len(P), len(evs) / blocks)
    show("launches (all lines)", lagh(Tabs, [b for b in launch_bn]), len(P), len(launch_bn) / blocks)
    show("token distributions", lagh(Tabs, dist_bn), len(P), len(dist_bn) / blocks)
    # other bot buys: the same-wallet's previous action
    wl = collections.defaultdict(list)
    for a in acts: wl[a["wallet"]].append(a["bn"])
    g = []
    for p in P:
        tw = next(a["wallet"] for a in acts if a["tx"] == p["Ttx"])
        v = [b for b in wl[tw] if b < p["Tbn"]]
        g.append(p["Tbn"] - v[-1] if v else None)
    gg = sorted(x for x in g if x is not None)
    print(f"T's wallet: previous action by the same wallet, blocks before T p10/50/90: {gg[len(gg)//10]}/{gg[len(gg)//2]}/{gg[9*len(gg)//10]} (none before: {g.count(None)}); <=60: {sum(1 for x in gg if x <= 60)}")
    # nearest previous global bot action (any kind, other pools)
    allb = sorted(a["bn"] for a in acts)
    prev = []
    for p in P:
        i = bisect.bisect_left(allb, p["Tbn"]) - 1
        while i >= 0 and allb[i] == p["Tbn"]: i -= 1
        prev.append(p["Tbn"] - allb[i])
    print("T - previous bot action anywhere (blocks):", sorted(collections.Counter(prev).items())[:30])
