"""Chain (6 h): every non-bot, non-ours wallet buying in the line pools: pools, line, position relative to T, sizes, and the pull lag after its
buy (pull - buy offset), to see which buyers the operator reacts to. Also: for every pull inside the window, the last non-bot buy before it."""
import pickle, collections
from common import *
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]
W = collections.defaultdict(list)
for p in P:
    ib = next((i for i, s in enumerate(p["sw"]) if s["who"] == "bot"), None)
    for i, s in enumerate(p["sw"]):
        if not s["buy"] or s["who"] in ("bot", "ours"): continue
        rel = "noT" if ib is None else ("pre" if i < ib else "post")
        lag = None if p["pull"] is None else p["pull"] - s["off"]
        W[s["eoa"]].append(dict(line=p["line"], reg=p["regime"], off=s["off"], T=p["T"], rel=rel, q=s["q"] / 1e18, lag=lag, ours=p["ours"], to=s["to"][:10], nonce=s["nonce"], ts=p["ts"], span=p["span"]))
def lagtxt(v):
    k = lambda a, b: sum(1 for x in v if x is not None and a <= x <= b)
    return f"pull 0-10 after {k(0,10)}, 11-30 {k(11,30)}, 31-400 {k(31,400)}, none/later {sum(1 for x in v if x is None or x > 400)}"
print("wallet       n  lines            rel(pre/post/noT)  sizes                          via               nonce-range     | pull after its buy")
for w, v in sorted(W.items(), key=lambda kv: -len(kv[1])):
    ln = collections.Counter(x["line"] for x in v); rel = collections.Counter(x["rel"] for x in v)
    print(f"{w[:12]} {len(v):3d} {dict(ln)!s:18s} {rel.get('pre',0)}/{rel.get('post',0)}/{rel.get('noT',0):<3d} {str(collections.Counter(round(x['q'],6) for x in v).most_common(2)):32s} {str(collections.Counter(x['to'] for x in v).most_common(1)):20s} "
          f"{min(x['nonce'] or 0 for x in v)}-{max(x['nonce'] or 0 for x in v):<8d} | {lagtxt([x['lag'] for x in v])}; post-T offsets {sorted(x['off']-x['T'] for x in v if x['rel']=='post')[:8]}")
print("\nevery first pull inside the 400-block window, by line: the last non-bot, non-sentinel buy before it (who, size, blocks before the pull), the bot's state")
for line in ("2.433", "3.0"):
    c = collections.Counter()
    for p in sorted(P, key=lambda p: p["lb"]):
        if p["line"] != line or p["pull"] is None: continue
        pre = [s for s in p["sw"] if s["buy"] and s["who"] not in ("bot", "sentinel") and s["off"] <= p["pull"]]
        last = pre[-1] if pre else None
        bots = [s for s in p["sw"] if s["who"] == "bot"]
        tag = "ours" if p["ours"] else ""
        d = None if last is None else p["pull"] - last["off"]
        c[("no buyer" if last is None else ("<=10" if d <= 10 else "11-30" if d <= 30 else ">30"))] += 1
        print(f"  {line} {utc(p['ts'])} {p['regime']:20s} {tag:4s} T {p['T']} bots {len(bots)} pull +{p['pull']} last buyer " + (f"{last['eoa'][:10]} {last['q']/1e18:.6f} at +{last['off']} ({d} before)" if last else "none"))
    print(" ", line, dict(c))
