# Post-census activity of every judged family, from the census head (block 85,203,898) to the chain head: ETH-pair v4 Initialize logs
# counted by fingerprint (fee, tick spacing, hooks, launch sqrtP), per 1-hour bucket (36,000 blocks), with the last launch block.
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, PM, T_INIT, W, sgn
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/headcheck3.json"
a = 85203898
head = int(rpc("eth_blockNumber", []), 16)
hb = rpc("eth_getBlockByNumber", [hex(head), False]); hts = int(hb["timestamp"], 16)
ab = rpc("eth_getBlockByNumber", [hex(a), False]); ats = int(ab["timestamp"], 16)
ZERO = "0x" + "0" * 64
L = logs({"address": PM, "topics": [T_INIT, None, ZERO]}, a, head)
C2 = {3961408125713221831437354658330384, 4574240095501000877149679564623533, 3543191142285917749113176609134040, 4234923421600340949702393012134791}
POT = {5602277097478613991873193822745817, 5905318570476523676536723872024200}
def classify(fee, ts, hz, sp):
    if (fee, ts, sp) == (2500, 50, 1604517591721945638372359205383840) and hz: return "v2.433"
    if (fee, ts, sp) == (10000, 200, 679394651928963067279918579724198) and hz: return "v3.0"
    if (fee, ts, sp) == (10000, 200, 526364174002223567019744861584709) and hz: return "v5.0"
    if (fee, ts, sp) == (10000, 200, 1908498483466244238266951834509291) and hz: return "new fee10000/ts200 sqrtP 1.908e33"
    if fee == 100 and ts == 1 and hz and sp in (792280926924313289846529216293289, 835109957917073511657837871095390): return "C-1 (2276, fee 100)"
    if fee == 500 and ts == 1 and hz and sp in C2: return "C-2 (PM 196, fee 500)"
    if hz and ((fee, ts) in ((100, 1), (500, 10))) and sp in POT: return "small pot (sqrtP match)"
    if (fee, ts, sp) == (2500, 25, 2506289003612544606728200307581467) and not hz: return "hooked one-off f07d1c53"
    if hz and 10001 <= fee <= 10300 and ts in (200, 201): return "vbot other sizes (fee 10001-10300)"
    return "other"
cnt = collections.Counter(); last = {}; first = {}; byh = collections.defaultdict(collections.Counter); ex = {}
oth = collections.Counter()
for l in L:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hz = d[2 + 64 * 2 + 24:2 + 64 * 3] == "0" * 40; sp = W(d, 3)
    k = classify(fee, ts, hz, sp); bn = int(l["blockNumber"], 16)
    cnt[k] += 1; last[k] = max(last.get(k, 0), bn); first[k] = min(first.get(k, 10**12), bn); byh[k][(bn - a) // 36000] += 1
    ex.setdefault(k, []).append(l["transactionHash"]) if len(ex.get(k, [])) < 3 else None
    if k == "other": oth[(fee, ts, hz, str(sp))] += 1
spb = (hts - ats) / (head - a)
utc = lambda b: time.strftime("%Y-%m-%d %H:%M", time.gmtime(ats + (b - a) * spb))
res = {"from_block": a, "from_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ats)), "head": head,
       "head_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(hts)), "hours": round((hts - ats) / 3600, 2), "s_per_block": round(spb, 5),
       "n_eth_inits": len(L), "by_family": dict(cnt.most_common()), "first_utc": {k: utc(b) for k, b in first.items()},
       "last_block": last, "last_utc": {k: utc(b) for k, b in last.items()},
       "per_hour": {k: [byh[k].get(i, 0) for i in range((head - a) // 36000 + 1)] for k in cnt},
       "examples": ex, "other_top": [[list(k), n] for k, n in oth.most_common(15)]}
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps({k: res[k] for k in res if k not in ("examples",)}, indent=1))
