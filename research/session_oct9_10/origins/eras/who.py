"""who.py addr...: launches each address created or bought in (component, time, value)"""
from L import *
X = launches(); R = json.load(open(D + "p1.json")); Lp = json.load(open(D + "p2_loops.json"))
comp = {}
for l in Lp:
    for h in l["launches"]: comp[h] = "L%03d" % l["i"]
_IDX = collections.defaultdict(list)
for x in X:
    _IDX[x["from"]].append(("CREATE", x))
    for t in {t for n, t, h in R[x["h"]]["buys"]}: _IDX[t].append(("buy", x))
def who(a, k=6):
    v = sorted(_IDX.get(a.lower(), []), key=lambda z: z[1]["bn"])
    if not v: return f"{a}: no launch activity"
    cc = collections.Counter((r, comp.get(x["h"], "fresh")) for r, x in v)
    s = "; ".join(f"{r} {comp.get(x['h'],'fresh')} {x['bn']} {T(x['bn'])} v{round(x['value'],3)}" for r, x in v[:k])
    return f"{a}: {len(v)} [{dict(cc)}] first/last {T(v[0][1]['bn'])} .. {T(v[-1][1]['bn'])} :: {s}"
if __name__ == "__main__":
    for a in sys.argv[1:]: print(who(a))
