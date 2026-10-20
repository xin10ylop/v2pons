"""shared helpers for analyst B's scripts"""
import json, os, collections as C, statistics as S
D = os.path.dirname(os.path.abspath(__file__))
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
FROM_TS = 1791121962          # window start (Oct 4 13:52:42 UTC); day d = [FROM_TS + 86400 d, + 86400); d6 = the last 24 h
DAYS = ["10-04", "10-05", "10-06", "10-07", "10-08", "10-09", "10-10*"]   # day d starts at 13:52 UTC of that date; 10-10* = the last 24 h
def day(r): return min(6, max(0, int((r["launch_ts"] - FROM_TS) // 86400)))
def load_rows():
    return [json.loads(l) for l in open(os.path.join(D, "b_pools.jsonl"))]
def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
def p3(xs):
    v = [pct(xs, q) for q in (0.1, 0.5, 0.9)]
    return "/".join("-" if x is None else (f"{x:.0f}" if abs(x) >= 10 or x == int(x) else f"{x:.3g}") for x in v)
def med(xs):
    xs = [x for x in xs if x is not None]; return S.median(xs) if xs else None
def top(xs, k=2, w=None):
    c = C.Counter(xs); n = sum(c.values()) or 1
    return ", ".join(f"{a if w is None else str(a)[:w]} {b/n:.0%}" for a, b in c.most_common(k))
def topshare(xs):
    c = C.Counter(xs); n = sum(c.values()); return (c.most_common(1)[0][1] / n) if n else None
def key_of(r, g):
    f = r["fam"]
    if g == "lt": return (f.get("lc") or "none") + "#" + (f.get("tok") or "none")[:8]
    return f.get(g) or "none"
def short(k):
    if "@" in k:
        a, b = k.split("@"); return short(a) + "@" + b
    if "#" in k:
        a, b = k.split("#"); return short(a) + "#" + b
    if "|" in k:
        p = k.split("|"); return p[0][:8] + "|" + "|".join(p[1:])
    return k[:8]
