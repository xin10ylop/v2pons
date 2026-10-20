"""Classify every token arriving at the bot router by the launch of its pool; hourly table; anything not 3.0/5.0/2.433."""
import kc, json, collections, time, bisect
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
lg = []
for l in open(kc.p("k03_botin_cache.jsonl")): lg += json.loads(l)["logs"]
# timestamp grid
blocks = sorted(set(int(l["blockNumber"], 16) for l in lg))
grid = list(range(blocks[0] - blocks[0] % 10000, blocks[-1], 10000)) + [blocks[-1]]
bt = kc.block_ts_map("k04_grid_cache.jsonl", grid)
def tsof(b):
    i = bisect.bisect_right(grid, b) - 1; b0, b1 = grid[i], grid[min(i + 1, len(grid) - 1)]
    if b1 == b0: return bt[b0]
    return bt[b0] + (bt[b1] - bt[b0]) * (b - b0) / (b1 - b0)
tok2l = {}
for r in rows:
    for c in (r["c0"], r["c1"]):
        if c != "0x" + "0" * 40: tok2l.setdefault(c, []).append(r)
def fam(r):
    if r is None: return "nolaunch-in-window"
    v = r["value"] or 0
    if v == kc.V2433: return "2.433"
    if r["sqrtp"] == 679394651928963067279918579724198: return "3.0(sqrtP)"
    if r["sqrtp"] == 526364174002223567019744861584709: return "5.0(sqrtP)"
    return "OTHER v=%.6f fee=%d ts=%d sq=%.4e hooks=%s to=%s" % (v / 1e18, r["fee"], r["ts"], r["sqrtp"], r["hooks"][-6:], (r["to"] or "")[:10])
LAST = 86310320
hourly = collections.defaultdict(collections.Counter); other = collections.Counter(); src = collections.Counter(); mints = collections.defaultdict(collections.Counter)
famvals = collections.defaultdict(collections.Counter)
for l in lg:
    b = int(l["blockNumber"], 16); frm = kc.topaddr(l["topics"][1]); tok = l["address"].lower()
    L = tok2l.get(tok); r = L[0] if L else None
    f = fam(r); h = time.strftime("%m-%d %H", time.gmtime(tsof(b)))
    if r: famvals[f][(r["value"], r["fee"], r["ts"])] += 1
    if frm == "0x" + "0" * 40:
        mints[h][f] += 1; continue
    src[frm] += 1
    hourly[h][f] += 1
    if b > LAST and not f.startswith(("3.0", "5.0")): other[(f, tok)] += 1
print("sources of non-mint transfers into BOT:", src.most_common(5))
fams = ["2.433", "3.0(sqrtP)", "5.0(sqrtP)"]
print("hour      " + "  ".join("%10s" % f for f in fams) + "   other  | mints by fam")
for h in sorted(hourly):
    oth = sum(v for k, v in hourly[h].items() if k not in fams)
    print(h, "  ".join("%10d" % hourly[h][f] for f in fams), "%7d" % oth, " |", dict(mints[h]))
print("\nfamily (value,fee,ts) variants:")
for f in famvals:
    if not f.startswith("OTHER"): print(" ", f, dict(famvals[f]))
print("\nbuys after block %d in non-3.0/5.0 tokens:" % LAST, sum(other.values()))
for (f, tok), n in other.most_common(30): print("  ", n, tok, f)
# last 2.433 buy
l2 = [l for l in lg if fam((tok2l.get(l["address"].lower()) or [None])[0]) == "2.433" and kc.topaddr(l["topics"][1]) != "0x" + "0" * 40]
lb = max(int(l["blockNumber"], 16) for l in l2)
print("last bot buy in a 2.433 pool: block", lb, "~", kc.ts(tsof(lb)), "token", [l["address"] for l in l2 if int(l["blockNumber"], 16) == lb][0])
