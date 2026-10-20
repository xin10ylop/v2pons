"""Skeptic step 9: are v3.0 / v5.0 / v2.433 launched by one scheduler? Co-occurrence per 2-minute bucket over the census + fresh data, gaps, and the
inter-launch spacing; plus the time of the last launch of each in the fresh data."""
import sys, json, collections, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import rpc
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
P = load_pools()
fp = {(10000, 200, 679394651928963067279918579724198): "v3.0", (10000, 200, 526364174002223567019744861584709): "v5.0", (2500, 50, 1604517591721945638372359205383840): "v2.433"}
ev = []
for p in P.values():
    k = fp.get((p["fee"], p["tick_spacing"], p["sqrt_p0"]))
    if k and p["hooks_zero"] and p["launch_value_wei"] > 0: ev.append((p["launch_block"], k))
fresh = json.load(open(HERE + "/fresh/pools.json"))
ev += [(p["b0"], p["sub"]) for p in fresh]
ev.sort()
B = 1200  # ~2 minutes
bk = collections.defaultdict(collections.Counter)
for b, k in ev: bk[b // B][k] += 1
lo, hi = min(bk), max(bk)
cnt = collections.Counter()
for i in range(lo, hi + 1):
    c = bk.get(i, {})
    key = tuple(sorted(k for k in ("v3.0", "v5.0", "v2.433") if c.get(k)))
    cnt[key] += 1
out = {"buckets_2min": {"|".join(k) or "none": n for k, n in cnt.most_common()}}
# correlation of activity: fraction of active v2.433 buckets that also have v3.0, and vice versa
act = {k: set(i for i in bk if bk[i].get(k)) for k in ("v3.0", "v5.0", "v2.433")}
out["v3_active_also_v2433"] = round(len(act["v3.0"] & act["v2.433"]) / len(act["v3.0"]), 3)
out["v2433_active_also_v3"] = round(len(act["v2.433"] & act["v3.0"]) / len(act["v2.433"]), 3)
out["v3_active_also_v5"] = round(len(act["v3.0"] & act["v5.0"]) / len(act["v3.0"]), 3)
out["n_buckets"] = hi - lo + 1
# longest gaps per family (blocks)
for k in ("v3.0", "v5.0", "v2.433"):
    bs = [b for b, kk in ev if kk == k]
    gaps = sorted(((bs[i + 1] - bs[i], bs[i]) for i in range(len(bs) - 1)), reverse=True)[:4]
    out["gaps_" + k] = [(g, b) for g, b in gaps]; out["last_" + k] = bs[-1]
head = int(rpc("eth_blockNumber", []), 16)
ts = lambda b: int(rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
out["head"] = head; out["head_utc"] = datetime.datetime.fromtimestamp(ts(head), datetime.UTC).isoformat()
for k in ("v3.0", "v5.0", "v2.433"): out["last_utc_" + k] = datetime.datetime.fromtimestamp(ts(out["last_" + k]), datetime.UTC).isoformat()
print(json.dumps(out, indent=1))
json.dump(out, open(HERE + "/s9_schedule.json", "w"), indent=1)
