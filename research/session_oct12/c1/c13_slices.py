"""6-h slices (by launch time, ending at the c01 head) of pull-by-T+62 / T+120 / T+200 for: pools with a non-dust outsider holding at T+62 (c11's
definition), our relay's fills, and the rest; plus the early non-dust outsiders in (T, T+10]. (offline, c05)"""
from common import *
D = json.load(open(J("c05_pools.json"))); P = D["pools"]; M = json.load(open(J("c01_meta.json")))
OUT = ("recurring", "oneoff")
TP = [p for p in P if p["T"] is not None and p["age"] >= p["T"] + 300]
def grp(p):
    if any(s["cls"] == "ours" and s["buy"] for s in p["sw"]): return "ours"
    end = min(p["T"] + 62, p["pull"] if p["pull"] is not None else 1 << 40)
    for s in p["sw"]:
        if not (s["buy"] and s["cls"] in OUT and s["eth"] >= 0.001 and s["off"] <= p["T"] + 62): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        if not [x for x in p["sw"] if not x["buy"] and x.get("from") == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end]: return "holder"
    return "rest"
early = lambda p: any(s["buy"] and s["cls"] in OUT and s["eth"] >= 0.001 and (s["bn"], s["li"]) > tuple(p["Tpos"]) and s["off"] - p["T"] <= 10 for s in p["sw"])
e = M["head_ts"]
print("slice (UTC)            launches trig  | rest: by T+62 / T+120 / T+200     | holder: T+62/120/200 | ours: T+62/120/200 | early non-dust outsider in (T,T+10]: n, pulled by T+62")
for k in range(6, 0, -1):
    a, b = e - 6 * 3600 * k, e - 6 * 3600 * (k - 1)
    G = [p for p in TP if a <= p["ts"] < b]; nl = sum(1 for p in P if a <= p["ts"] < b)
    def f(g):
        pts = [p["pull"] - p["T"] for p in G if grp(p) == g and p["pull"] is not None]; n = sum(1 for p in G if grp(p) == g)
        return f"{sum(1 for x in pts if x <= 62)}/{sum(1 for x in pts if x <= 120)}/{sum(1 for x in pts if x <= 200)} of {n}"
    E = [p for p in G if early(p)]
    print(f"{utc(a)}-{utc(b)[6:]}  {nl:4d} {len(G):4d}  | {f('rest'):>22s}          | {f('holder'):>14s}       | {f('ours'):>10s}     | {len(E)}, {sum(1 for p in E if p['pull'] is not None and p['pull'] <= p['T'] + 62)}")
