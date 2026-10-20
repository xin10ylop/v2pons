"""a check from the logs alone (no transactions): the + 1 bot (Swap sender = its contract 0x570759db) bought in many line pools at + 1 and
almost never sells there. Pools with its + 1 buy against pools without, per launch day: the first buy >= 0.005 ETH by anyone (W's 'first
real buy'; 855 of 906 are the crowd's in the census), the pull (first Burn with liquidity), pulls inside + 80, the replay at Q ETH (default 0.002, $5)."""
from common import *
import collections
from wcommon import compact
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
rows = []
for line in open(J("r02_events_cache.jsonl")):
    e = json.loads(line); x = L[e["pool"]]; qs = x["qs"]; lb = x["lb"]
    ev = [c for c in (compact(l) for l in sorted(e["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))) if c]
    pull = next((c[1] - lb for c in ev if c[0] == "b" and c[8] > 0), None)
    if pull is None:
        bb = [compact(l) for l in (B.get(x["pool"]) or {}).get("burns", [])]; bb = sorted(c[1] - lb for c in bb if c and c[8] > 0); pull = bb[0] if bb else None
    sw = [c for c in ev if c[0] == "s"]
    bot = any(c[5].startswith("0x570759db") and c[1] - lb <= 2 and (c[7] if qs == 0 else c[8]) > 0 for c in sw)
    frb = next((c[1] - lb for c in sw if (c[7] if qs == 0 else c[8]) >= 5e15), None)
    trig = next((c[1] - lb for c in sw if c[1] - lb >= 2 and (c[7] if qs == 0 else c[8]) >= 5e15), None)
    sell = min(trig + 20, 80) if trig is not None else 80
    r = replay({"dex": "v3", "quote_side": qs, "fee": 100}, {"lb": lb, "ev": ev, "ev_to": e["to"]}, 2, sell, float(os.environ.get("Q", "0.002")))
    rows.append({"day": time.strftime("%m-%d", time.gmtime(x["ts"])), "bot": bot, "frb": frb, "pull": pull, "ret": r.get("ret") if r["ok"] else None, "sell": sell, "end": e["to"] - lb})
def show(lab, g):
    n = len(g)
    if not n: return
    fr = [z["frb"] for z in g if z["frb"] is not None]; pl = [z["pull"] for z in g if z["pull"] is not None]
    rs = [z["ret"] for z in g if z["ret"] is not None]
    p80 = sum(1 for z in g if z["pull"] is not None and z["pull"] <= z["sell"]); p150 = sum(1 for z in g if z["pull"] is not None and z["pull"] <= 150)
    nf = sum(1 for z in g if z["frb"] is None or (z["pull"] is not None and z["pull"] < z["frb"]))
    print(f"  {lab:<12} n {n:>4} first real buy by +78 {sum(1 for f in fr if f <= 78)/n:5.1%}  median {pct(fr,.5)}  none before the pull {nf/n:5.1%}  pulled<=sell {p80}  <=150 {p150/n:5.1%}"
          f"  pull median {pct(pl,.5)}  rule mean {sum(rs)/len(rs)*100:+.2f}% median {pct(rs,.5)*100:+.3f}%")
    return n, p150, nf
print("+1 bot present (its contract bought at + 1..+ 2) or not")
a = show("bot", [z for z in rows if z["bot"]]); b = show("no bot", [z for z in rows if not z["bot"]])
print("  Fisher pulled <= +150 (bot higher):", fisher(a[1], a[0] - a[1], b[1], b[0] - b[1]), " no real buy before the pull:", fisher(a[2], a[0] - a[2], b[2], b[0] - b[2]))
for d in sorted({z["day"] for z in rows}):
    print(d); show("bot", [z for z in rows if z["bot"] and z["day"] == d]); show("no bot", [z for z in rows if not z["bot"] and z["day"] == d])
print("\npull relative to the first real buy (pools with one before the pull), bot / no bot")
for lab, g in (("bot", [z for z in rows if z["bot"]]), ("no bot", [z for z in rows if not z["bot"]])):
    h = [z for z in g if z["frb"] is not None and (z["pull"] is None or z["pull"] > z["frb"])]
    d = [z["pull"] - z["frb"] for z in h if z["pull"] is not None]
    n = len(h)
    print(f"  {lab:<7} n {n}: pull - first real buy p5/10/25/50 {pct(d,.05)}/{pct(d,.1)}/{pct(d,.25)}/{pct(d,.5)};"
          + "  ".join(f" <= +{k}: {sum(1 for v in d if v <= k)} ({sum(1 for v in d if v <= k)/n:.1%})" for k in (20, 40, 60, 100, 150, 300)))
print("\nno real buy before the pull: when the pull came, bot / no bot")
for lab, g in (("bot", [z for z in rows if z["bot"]]), ("no bot", [z for z in rows if not z["bot"]])):
    h = [z["pull"] for z in g if z["pull"] is not None and (z["frb"] is None or z["frb"] > z["pull"])]
    print(f"  {lab:<7} n {len(h)}: pull p5/10/25/50 {pct(h,.05)}/{pct(h,.1)}/{pct(h,.25)}/{pct(h,.5)}; <= 80: {sum(1 for v in h if v <= 80)}, <= 100: {sum(1 for v in h if v <= 100)}, <= 150: {sum(1 for v in h if v <= 150)}")
