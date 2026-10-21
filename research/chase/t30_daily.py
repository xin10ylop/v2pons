#!/usr/bin/env python3
"""t30_daily.py FILE.json [FILE.json ...] [--usd 2570]: the Robinhood V2 30.09 ETH tier's seat (v2tier_scan.py files), per UTC day: pairs,
the seat's P&L at 0.004 ETH bought at N+1 and sold at 20 / 25 / 30 minutes (or 1 s after a foreign buy of >= 0.005 ETH; -100% when the pull
comes first), and the detector: the largest foreign buy left alone and the smallest one pulled within 400 blocks."""
import json, sys, collections, statistics as st, urllib.request, concurrent.futures as cf, datetime
U = "https://rpc.mainnet.chain.robinhood.com"; USD = 2570.0; files = []
args = sys.argv[1:]
while args:
    a = args.pop(0)
    if a == "--usd": USD = float(args.pop(0))
    else: files.append(a)
rpc = lambda m, p: json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=30))["result"]
P, txs = {}, {}
for f in files:
    d = json.load(open(f)); P.update(d["pairs"]); txs.update(d["txs"])
BAIT = {w for w, n in collections.Counter(t[0] for t in txs.values() if t).items() if n > 300}
DUST = {"0e77610e9f13062c2eaa709ef1c59b8c22e549c9", "43745495eb9295aa5b4894f7ba6b4163a19aef32", "e71a69f434a719cd5afa411568b69716aab3b84a", "71a803347d69b00010365684d0517c36c2265c25"}
with cf.ThreadPoolExecutor(8) as ex:
    ts = dict(zip(P, ex.map(lambda p: int(rpc("eth_getBlockByNumber", [hex(p["bn"]), False])["timestamp"], 16), P.values())))
out = lambda x, ri, ro: x * 997 * ro // (ri * 1000 + x * 997)
GAS = 2 * 0.0000027; S = int(0.004e18); EXITS = (20, 25, 30)
days = collections.defaultdict(lambda: {"n": 0, "pnl": {T: 0.0 for T in EXITS}, "win": {T: 0 for T in EXITS}, "pulled": {T: 0 for T in EXITS}, "oexit": 0, "ok": [], "hit": []})
for a, p in P.items():
    day = datetime.datetime.fromtimestamp(ts[a], datetime.timezone.utc).strftime("%m-%d"); D = days[day]; D["n"] += 1
    w0 = p["weth_is0"]; m = p["mints"][0]; e, t = (m[1], m[2]) if w0 else (m[2], m[1]); N = p["bn"]; burn = p["burns"][0][0] if p["burns"] else None
    ends = {N: (e, t)}; trig = None
    for s in sorted(p["swaps"], key=lambda s: (s[0], s[1])):
        ein, eout, tin, tout = (s[2], s[4], s[3], s[5]) if w0 else (s[3], s[5], s[2], s[4])
        e += ein - eout; t += tin - tout; ends[s[0]] = (e, t); who = (txs.get(s[6]) or ["?"])[0]
        if ein and who not in BAIT and who not in DUST and s[0] > N and (burn is None or s[0] < burn):
            (D["hit"] if burn is not None and burn - s[0] <= 400 else D["ok"]).append(ein / 1e18)
            if trig is None and ein >= 0.005e18 and s[0] > N + 1: trig = s[0]
    at = lambda b: ends[max(k for k in ends if k <= b)]
    e1, t1 = at(N + 1); tok = out(S, e1, t1); val = lambda b: out(tok, at(b)[1] - tok, at(b)[0] + S)
    for T in EXITS:
        X = trig + 10 if trig is not None and trig + 10 < N + T * 600 else N + T * 600
        if T == 25 and X != N + T * 600: D["oexit"] += 1
        r = -1.0 if burn is not None and burn <= X else val(X) / S - 1
        D["pnl"][T] += 0.004 * r - GAS; D["win"][T] += r > 0; D["pulled"][T] += r == -1.0
print("day   pairs | 25-min exit: P&L ETH (USD), won, pulled, sold on a foreign buy | 20 min P&L | 30 min P&L | foreign buys: largest left alone / smallest pulled")
tot = {T: 0.0 for T in EXITS}; n = 0
for day in sorted(days):
    D = days[day]; n += D["n"]; [tot.__setitem__(T, tot[T] + D["pnl"][T]) for T in EXITS]
    print("%s  %3d  | %+.5f ($%+6.2f) %2d won %d pulled %d sold | %+.5f | %+.5f | %s / %s" % (day, D["n"], D["pnl"][25], D["pnl"][25] * USD, D["win"][25], D["pulled"][25], D["oexit"],
          D["pnl"][20], D["pnl"][30], ("%.4f" % max(D["ok"])) if D["ok"] else "-", ("%.4f" % min(D["hit"])) if D["hit"] else "-"))
nd = len(days); print("total %d pairs over %d days: 25 min %+.4f ETH ($%.0f, $%.0f a day); 20 min %+.4f ETH; 30 min %+.4f ETH" % (n, nd, tot[25], tot[25] * USD, tot[25] * USD / nd, tot[20], tot[30]))
