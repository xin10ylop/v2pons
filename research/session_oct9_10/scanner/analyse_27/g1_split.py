"""G1 (POSM ac9650d8 2020 bytes) split into sub-clusters: by deployer, by launch range, by fee; front and follow per cluster (common27 pricer)"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common27 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
G = [p for p in P.values() if p["launch_to"] == POSM and p["selector"] == "ac9650d8" and p["calldata_len"] == 2020]
E = load_events(set(p["pid"] for p in G))
PL = {p["pid"]: Pool(p, E.get(p["pid"]), T, M) for p in G}
def real(pl, after=None): return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]
def front(pl, hold=20):
    B = pl.b0 + 1; r = real(pl, B); sb = r[0] if r else None
    S = sb["bn"] + 1 if (sb and sb["bn"] + 1 <= pl.b0 + hold) else pl.b0 + hold
    o = pl.trade(B, S); o["sched"] = (sb["bn"] - pl.b0) if sb else None; return o
def follow(pl, hold=4):
    rb = real(pl)
    if not rb: return None
    B = rb[0]["bn"] + 1; nx = next((x for x in rb if x["bn"] > B), None)
    S = nx["bn"] + 1 if (nx and nx["bn"] + 1 <= B + hold) else B + hold
    o = pl.trade(B, S); o["trig"] = rb[0]["bn"] - pl.b0; return o
out = {}
def clus(name, keyf):
    C = collections.defaultdict(list)
    for p in G: C[keyf(p)].append(p["pid"])
    res = []
    for k, pids in sorted(C.items(), key=lambda kv: -len(kv[1])):
        if len(pids) < 5: continue
        pls = [PL[x] for x in pids]
        fr = [real(pl) for pl in pls]
        row = {"key": str(k), "n": len(pids), "with_real_buy": sum(1 for r in fr if r), "first_real_off_p10_50_90": q([r[0]["bn"] - pl.b0 for pl, r in zip(pls, fr) if r]),
               "first_real_eth_p10_50_90": q([r[0]["eth"] / 1e18 for r in fr if r]), "first_real_from": collections.Counter(r[0]["from"] for r in fr if r).most_common(3),
               "pulled": sum(1 for pl in pls if pl.pull_bn), "pull_off_p10_50_90": q([pl.pull_bn - pl.b0 for pl in pls if pl.pull_bn]),
               "fees": collections.Counter(pl.fee_key for pl in pls).most_common(3), "deployers": len(set(PL[x].p["launch_from"] for x in pids)),
               "front": summarize([front(pl) for pl in pls]), "follow": summarize([z for z in (follow(pl) for pl in pls) if z])}
        res.append(row)
        print("%-55s n %3d realbuy %3d off %s eth %s pulled %d %s fees %s | FRONT %s | FOLLOW %s" % (str(k)[:55], row["n"], row["with_real_buy"], row["first_real_off_p10_50_90"], row["first_real_eth_p10_50_90"], row["pulled"], row["pull_off_p10_50_90"], row["fees"], fmt_rule(row["front"]), fmt_rule(row["follow"])))
    out[name] = res
print("== by deployer"); clus("deployer", lambda p: p["launch_from"])
print("== by launch range"); clus("range", lambda p: str([(a["lo"], a["hi"]) for a in PL[p["pid"]].adds if a["tx"] == p["launch_tx"]]))
print("== by fee"); clus("fee", lambda p: p["fee"])
print("== by hooks_zero"); clus("hooks_zero", lambda p: p["hooks_zero"])
# follow drivers: the pools that make G1's follow mean
fo = [(pl.pid, z) for pl in PL.values() for z in [follow(pl)] if z and z.get("ret") is not None]
fo.sort(key=lambda t: -t[1]["ret"])
out["follow_top"] = [{"pid": a, "ret": round(z["ret"], 4), "trig": z["trig"], "fee": PL[a].fee_key, "from": PL[a].p["launch_from"]} for a, z in fo[:8]]
print("follow top", out["follow_top"])
print("follow without the top 3:", fmt_rule(summarize([z for a, z in fo[3:]])))
json.dump(out, open(os.path.join(HERE, "g1_split.json"), "w"), indent=1, default=str)
