"""own per-pool build (independent of reaction/rlib.py): swaps to + 300 (WIN of s02) with their tx's sender and call shape where fetched (to + 80,
s03), the pull (first Burn with liquidity > 0), the crowd's first real buy, the engine's trigger and our sell, and every outside wallet's
position by block. Crowd = a crowd-shaped call (3593564c/484, a0193551/452, 49f74a5d/452) not to the UR, or any tx from such a call's EOA or to
its contract; a swap whose tx was not fetched (after + 80) is the crowd's when its Swap sender is a crowd contract or its recipient a crowd
EOA/contract. -> s04_pools_cache.jsonl"""
from common import *
import collections
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"
L = {x["pool"]: x for x in json.load(open(J("s01_launches.json")))}
E = {e["pool"]: e for e in jl(J("s02_logs_cache.jsonl"))}
T = {t["hash"]: t for t in jl(J("s03_txs_cache.jsonl"))}
CE, CC = collections.Counter(), collections.Counter()
for t in T.values():
    if (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR: CE[t["from"]] += 1; CC[t["to"]] += 1
print(f"pools {len(L)} with logs {len(E)}; txs {len(T)}; crowd-shaped txs {sum(CC.values())}: EOAs {len(CE)}, contracts {len(CC)}")
REAL = 5 * 10 ** 15
out = []; cls = collections.Counter(); sndr = collections.Counter()
for pool, x in L.items():
    e = E.get(pool)
    if not e: continue
    lb = x["lb"]; qs = x["qs"]; sw = []; pull = None
    for c in e["ev"]:
        if c[0] == "b" and c[7] > 0 and pull is None:
            bt = T.get(c[10]); pull = {"off": c[1] - lb, "bn": c[1], "li": c[3], "from": bt["from"] if bt else None, "tx": c[10]}
        if c[0] != "s": continue
        if pull is not None: break
        dq = c[6] if qs == 0 else c[7]; dt = c[7] if qs == 0 else c[6]; t = T.get(c[11])
        if t is None:
            k = "crowd_s" if (c[4] in CC or c[5] in CE or c[5] in CC) else "unf"
        elif t["from"] == x["lw"]: k = "lw"
        elif (t["sel"], t["len"]) in CROWD_SHAPES and t["to"] != UR: k = "crowd"
        elif t["from"] in CE or t["to"] in CC: k = "crowd2"
        else: k = "other"
        if t is not None and k in ("crowd", "crowd2"): sndr[("crowd", c[4] in CC, c[5] in CE or c[5] in CC)] += 1
        if t is not None and k == "other": sndr[("other", c[4] in CC, c[5] in CE or c[5] in CC)] += 1
        cls[k] += 1
        sw.append({"off": c[1] - lb, "ti": c[2], "li": c[3], "dq": dq, "dt": dt, "k": k, "snd": c[4], "rcp": c[5], "tx": c[11],
                   "from": t["from"] if t else None, "to": t["to"] if t else None, "sel": t["sel"] if t else None, "len": t["len"] if t else None,
                   "val": t["value"] if t else None, "bot": bool(t and t["from"] == BOT1)})
    crowdish = lambda s: s["k"] in ("crowd", "crowd2", "crowd_s")
    frb = next((s["off"] for s in sw if crowdish(s) and s["dq"] >= REAL), None)
    # the engine's trigger: at or after + 2, >= 0.005 ETH, the crowd's shapes through any contract (the UR's 484-byte execute included) or anyone's ETH-value buy
    def trig_ok(s):
        if s["off"] < 2 or s["dq"] < REAL: return False
        if crowdish(s): return True
        if s["k"] in ("other", "lw") and ((s["val"] or 0) > 0 or (s["sel"], s["len"]) in CROWD_SHAPES): return True
        return False
    trig = next((s["off"] for s in sw if trig_ok(s)), None)
    trig_an = next((s["off"] for s in sw if s["off"] >= 2 and s["dq"] >= REAL and (s["k"] in ("crowd", "crowd2", "crowd_s") or (s["k"] == "other" and (s["val"] or 0) > 0))), None)
    out.append({"pool": pool, "lb": lb, "ts": x["ts"], "qs": qs, "lw": x["lw"], "sqrtp": x["sqrtp"], "win": e["to"] - lb, "pull": pull, "frb": frb, "trig": trig, "trig_an": trig_an,
                "sell": min(trig + 20, 80) if trig is not None else 80, "sw": sw})
open(J("s04_pools_cache.jsonl"), "w").write("".join(json.dumps(p) + "\n" for p in out))
print("classes", dict(cls))
print("Swap sender/recipient vs class (fetched txs): (class, sender is a crowd contract, recipient crowd EOA/contract) ->", sorted(sndr.items(), key=lambda kv: -kv[1])[:10])
print("pulled within the window", sum(1 for p in out if p["pull"]), "of", len(out), "; pull from = launch wallet", sum(1 for p in out if p["pull"] and p["pull"]["from"] == p["lw"]),
      "of", sum(1 for p in out if p["pull"] and p["pull"]["from"]))
