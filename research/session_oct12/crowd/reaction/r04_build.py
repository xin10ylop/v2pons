"""per-pool records of the v3crowd line: the launch, every Swap up to the first Burn (or launch + 3000) with its transaction's sender and
call shape, and the first Burn (the pull). Classes: 'crowd' (a crowd-shaped call (3593564c/484, a0193551/452, 49f74a5d/452) not sent to
the Universal Router, or any tx from an EOA / to a contract seen in such a call), 'lw' (the pool's launch wallet), 'other' (everyone else); a swap whose tx was not fetched (a buy later than the crowd's first + 30) is 'crowd_r' when its
recipient is a crowd EOA, or (a sell) its sender is the UR and its recipient a crowd contract, else 'unknown'.
-> r04_pools_cache.jsonl (one pool per line) and r04_build.out (counts)."""
from common import *
import collections
from wcommon import compact
L = json.load(open(J("r01_launches.json"))); M = json.load(open(J("r01_meta.json")))
E = {x["pool"]: x for x in jl(J("r02_events_cache.jsonl"))}; B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
T = {t["hash"]: t for t in jl(J("r03_txs_cache.jsonl"))}
print(f"launches {len(L)}, event files {len(E)}, long burns {len(B)}, txs {len(T)}")
crowd_eoa, crowd_to = collections.Counter(), collections.Counter()
for t in T.values():
    if (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR: crowd_eoa[t["from"]] += 1; crowd_to[t["to"]] += 1
print(f"crowd-shaped txs {sum(crowd_to.values())}: {len(crowd_eoa)} EOAs, {len(crowd_to)} contracts: {crowd_to.most_common(20)}")
def klass(t, lw, rcpt, snd=None):
    if t is None:                     # tx not fetched (a buy after the crowd's first + 30, or a crowd sell): by the Swap's recipient
        return "crowd_r" if rcpt in crowd_eoa or (snd == UR and rcpt in crowd_to) else "unknown"
    if t["from"] == lw: return "lw"
    if (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR: return "crowd"
    if t["from"] in crowd_eoa or t["to"] in crowd_to: return "crowd2"
    return "other"
out = open(J("r04_pools_cache.jsonl"), "w"); cnt = collections.Counter(); miss = 0
for x in L:
    e = E.get(x["pool"])
    if not e: continue
    ls = sorted(e["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    ev = [c for c in (compact(l) for l in ls) if c]
    burns = [c for c in ev if c[0] == "b" and c[8] > 0]
    if burns: fb = burns[0]
    else:
        lb_ = [compact(l) for l in sorted((B.get(x["pool"]) or {}).get("burns", []), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))]
        lb_ = [c for c in lb_ if c and c[8] > 0]; fb = lb_[0] if lb_ else None
    qs = x["qs"]; sw = []
    for c in ev:
        if c[0] != "s": continue
        if fb and (c[1], c[3]) > (fb[1], fb[3]): break
        t = T.get(c[12]); k = klass(t, x["from"], c[6], c[5]); cnt[k] += 1; miss += t is None
        dq = c[7] if qs == 0 else c[8]; dt = c[8] if qs == 0 else c[7]
        sw.append({"off": c[1] - x["lb"], "bn": c[1], "ti": c[2], "li": c[3], "dq": dq, "dt": dt, "sp": c[9], "k": k, "from": t["from"] if t else None,
                   "to": t["to"] if t else None, "sel": t["sel"] if t else None, "len": t["len"] if t else None, "val": t["value"] if t else None, "tx": c[12],
                   "snd": c[5], "rcpt": c[6]})
    bt = T.get(fb[-1]) if fb else None
    rec = dict(x, ev=ev, win_to=e["to"], sw=sw, pull_off=(fb[1] - x["lb"]) if fb else None, pull_bn=fb[1] if fb else None, pull_li=fb[3] if fb else None,
               pull_from=bt["from"] if bt else None, pull_to=bt["to"] if bt else None, pull_liq=fb[8] if fb else None, head=M["head"])
    out.write(json.dumps(rec) + "\n")
print("swap classes", dict(cnt), "tx missing", miss)
