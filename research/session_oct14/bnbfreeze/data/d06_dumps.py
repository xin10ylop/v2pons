"""d06: per pool, the reserves path summary: the dump (the first swap or burn taking >= 50% of the WBNB reserve; its tx sender), the
first crowd buy offset, the number of sells before L+260. -> d06_dumps.json"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *
LS = launches(); byp = {o["pair"]: o for o in LS}; P = pairlogs(); TX = txs()
ev = C.defaultdict(list)
for r in P: ev[r[4]].append(r)
out = {}
for pair, rs in ev.items():
    o = byp[pair]; rs.sort(key=lambda r: (r[0], r[1], r[2])); rq = rt = 0; dump = None
    for r in rs:
        if r[5] == "sync":
            q, t = (r[6], r[7]) if o["side"] == 0 else (r[7], r[6])
            if dump is None and rq > 0 and q <= rq * 0.5:
                dump = {"off": r[0] - o["L"], "blk": r[0], "tx": r[3], "from": (TX.get(r[3]) or [None])[0], "share": 1 - q / rq}
            rq, rt = q, t
    out[pair] = {"L": o["L"], "size": o["size"], "creator": o["creator"], "dump": dump, "dump_by_creator": (dump or {}).get("from") == o["creator"], "nlogs": len(rs)}
json.dump(out, open(os.path.join(D, "d06_dumps.json"), "w"))
print("pools", len(out), "with a dump", sum(1 for v in out.values() if v["dump"]), "dump by creator", sum(v["dump_by_creator"] for v in out.values()))
for s in (1.0, 2.5, 10.0, 15.0, 25.0):
    xs = sorted(v["dump"]["off"] for v in out.values() if v["size"] == s and v["dump"])
    print("size", s, "dumps", len(xs), "of", sum(1 for v in out.values() if v["size"] == s), "offsets min/median/max", xs[0] if xs else None, xs[len(xs) // 2] if xs else None, xs[-1] if xs else None)
