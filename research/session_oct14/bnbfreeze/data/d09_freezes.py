"""d09: the freezes. A freeze = the token's approve(target, ...) called by one of the operator's wallets (callers that approve a
non-router target in tokens they never held: 0xa70b3f34, 0xbd418ce6, 0xd6045405, 0x623e7c23). Matched to the buy census (d04/d05):
per freeze the target's first buy in that token and the delay; per non-crowd buyer whether and when it was frozen, and whether it moved
tokens out before the freeze. -> d09_freezes.json, d09_freezes.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *
A = [json.loads(l) for l in open(os.path.join(CACHE, "d08_tokenlogs_cache.jsonl"))]
F = [a for a in A if a[5] == "0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0"]
LS = launches(); byt = {o["token"]: o for o in LS}; TX = txs()
dd = json.load(open(os.path.join(CACHE, "d04_buyers_cache.json"))); B = dd["buys"]; OUTS = dd["outs"]; INS = dd["ins"]
st = json.load(open(os.path.join(D, "d05_status.json"))); CROWD = set(st["crowd"])
DU = json.load(open(os.path.join(D, "d06_dumps.json")))
holders = C.defaultdict(set)
for b in B: holders[b["token"]].add(b["buyer"])
for k in INS:
    t, a = k.split("|"); holders[t].add(a)
OPS = sorted(a for a, n in C.Counter(f[6] for f in F if f[7] != ROUTER and f[6] not in holders[f[4]]).items() if n >= 20)
print("operator freeze wallets:", OPS)
FZ = [f for f in F if f[6] in OPS]
# the freeze txs: sender, gas price (a freeze log's tx is not in the transfer tx cache: read them)
import rpc
need = sorted(set(f[3] for f in FZ) - set(TX))
got = rpc.batch([("eth_getTransactionByHash", [h]) for h in need], size=50)
ftx = {}
for h, r in zip(need, got):
    t = r.get("result") or {}
    ftx[h] = (t.get("from", "").lower(), (t.get("to") or "").lower(), t.get("input", "")[:10], int(t.get("gasPrice", "0x0"), 16), int(t.get("nonce", "0x0"), 16), t.get("input", "")[74:138])
print("freeze txs", len(FZ), "tx.from == log caller", sum(1 for f in FZ if ftx.get(f[3], (None,))[0] == f[6]), "selectors", C.Counter(ftx.get(f[3], ("", "", "?"))[2] for f in FZ),
      "gas price gwei", C.Counter(ftx.get(f[3], (0, 0, 0, 0))[3] / 1e9 for f in FZ).most_common(4), "amount word", C.Counter(ftx.get(f[3], ("",) * 6)[5][:8] for f in FZ).most_common(3))
first_buy = {}
for b in sorted(B, key=lambda b: (b["blk"], b["txi"])):
    first_buy.setdefault((b["token"], b["buyer"]), b)
first_in = {}
for k, v in INS.items():
    t, a = k.split("|")
    for i in v: first_in.setdefault((t, a), i)
frz = {}
for f in sorted(FZ, key=lambda f: (f[0], f[1], f[2])):
    frz.setdefault((f[4], f[7]), f)
rows = []
for (tok, tgt), f in frz.items():
    o = byt[tok]; b = first_buy.get((tok, tgt)); i = first_in.get((tok, tgt))
    rows.append({"token": tok, "pool": o["pair"], "size": o["size"], "code": o["code"]["size"], "L": o["L"], "target": tgt, "op": f[6], "fblk": f[0], "ftxi": f[1], "foff": f[0] - o["L"],
                 "crowd": tgt in CROWD, "buy_off": (b["blk"] - o["L"]) if b else None, "buy_blk": b["blk"] if b else None, "buy_txi": b["txi"] if b else None,
                 "delay": (f[0] - b["blk"]) if b else None, "in_off": (i["blk"] - o["L"]) if i else None, "sel": b["sel"] if b else None, "gp": b["gp"] if b else None,
                 "dump_off": (DU[o["pair"]]["dump"] or {}).get("off")})
C2 = C.Counter
print("freezes (distinct token,target)", len(rows), "crowd targets", sum(r["crowd"] for r in rows), "targets that bought", sum(r["buy_off"] is not None for r in rows),
      "targets that only received", sum(r["buy_off"] is None and r["in_off"] is not None for r in rows), "targets never holding", sum(r["buy_off"] is None and r["in_off"] is None for r in rows))
pre = [r for r in rows if r["buy_off"] is not None and r["delay"] < 0]
print("freezes BEFORE the target's first buy:", len(pre))
dl = sorted(r["delay"] for r in rows if r["delay"] is not None and r["delay"] >= 0)
q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]
print("delay buy -> freeze (blocks): n", len(dl), "min", dl[0], "p10", q(dl, .1), "median", q(dl, .5), "p90", q(dl, .9), "max", dl[-1])
print("delay histogram:", sorted(C2(min(d, 100) if d < 100 else (d // 100) * 100 for d in dl).items())[:40])
json.dump({"ops": OPS, "freeze_txs": ftx, "rows": rows}, open(os.path.join(D, "d09_freezes.json"), "w"), indent=0)
