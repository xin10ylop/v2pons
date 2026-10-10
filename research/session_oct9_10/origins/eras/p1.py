"""phase 1: for every launch, the pull block (first negative ModifyLiquidity on its pid within 200k blocks) and token buyers/sellers
(Transfer PM->x / x->PM) between launch and pull+20. Queries windowed to <=100k blocks (RPC limit)."""
from L import *
X = launches()
OUT = D + "p1.json"
R = {}
WIN = 100000
groups = collections.defaultdict(list)
for x in X: groups[x["bn"] // WIN].append(x)
def q(flt, a, b):
    for k in range(6):
        try: return logs(flt, a, b)
        except Exception as e: print("retry", a, b, e, flush=True); time.sleep(3 + 3 * k)
    raise RuntimeError("logs %d %d" % (a, b))
for gi, (g, ch) in enumerate(sorted(groups.items())):
    w0 = g * WIN
    for sub in range(0, len(ch), 60):
        cc = ch[sub:sub + 60]
        ev = []
        for k in range(2): ev += q({"address": PM, "topics": [T_ML, [x["pid"] for x in cc]]}, w0 + k * WIN, w0 + (k + 1) * WIN - 1)
        by = collections.defaultdict(list)
        for l in ev: by[l["topics"][1]].append((int(l["blockNumber"], 16), sgn(W(l["data"], 2)), l["transactionHash"]))
        end = {}
        for x in cc:
            e = sorted(by.get(x["pid"], []))
            neg = [v for v in e if v[1] < 0 and v[0] >= x["bn"]]
            R[x["h"]] = {"ml": [(v[0], str(v[1]), v[2]) for v in e], "pull": neg[0][0] if neg else None, "pulltx": neg[0][2] if neg else None}
            end[x["h"]] = min((neg[0][0] if neg else x["bn"] + 20000) + 20, w0 + 2 * WIN - 1)
        hi = max(end.values()); tr = []
        a = cc[0]["bn"]
        while a <= hi:
            b = min(hi, a + WIN - 1); tr += q({"address": [x["token"] for x in cc], "topics": [T_TR]}, a, b); a = b + 1
        byt = collections.defaultdict(list)
        for l in tr: byt[l["address"].lower()].append(l)
        for x in cc:
            buys, sells = [], []
            for l in byt.get(x["token"], []):
                n = int(l["blockNumber"], 16)
                if n > end[x["h"]] or n < x["bn"]: continue
                f, t = a32(l["topics"][1]), a32(l["topics"][2])
                if f == PM: buys.append((n, t, l["transactionHash"]))
                elif t == PM: sells.append((n, f, l["transactionHash"]))
            R[x["h"]]["buys"] = buys; R[x["h"]]["sells"] = sells
    if gi % 20 == 0:
        print("win", g, len(R), flush=True); json.dump(R, open(OUT, "w"))
json.dump(R, open(OUT, "w")); print("done", len(R), flush=True)
