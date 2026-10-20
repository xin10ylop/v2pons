"""d11b: the census-era (Oct 4-11) strangers of the 290 1/10/25-BNB pools: recipients of tokens from the pair (crowd = d10's 120 wallets,
plus the 0.051-gwei crowd wallets of that week = recipients in >= 20 of these pools that were never frozen) that bought before +990 (before
every tier's dump); whether the operator froze them, whether they moved tokens out before that, and today's transfer test.
-> d11b_census_strangers.json, .out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
RV = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/verify"
FP = json.load(open(RV + "/execution_PancakeSwap_V2_on_BNB_Chain__F_tok_9f0350f062d95ea48f746574ee0b7af7d643/out/e01_fam_pools.json"))
byt = {p["token"].lower(): p for p in FP}
R = [json.loads(l) for l in open(os.path.join(CACHE, "d11_census_cache.jsonl"))]
OPS = {"0x623e7c23c7c228095f94d9bd567eae55cb87a966", "0xa70b3f34e3ca7d4665b794ce6bb29168b1d2e40d", "0xbd418ce6a83995971de9f1cf9f61f345e91aeadd", "0xd604540564b6f659de163ad928e29782185da2fd"}
fz = {}
for r in sorted(R):
    if r[4] == "F" and r[5] in OPS and r[6] != ROUTER: fz.setdefault((r[3], r[6]), r)
T = sorted(r for r in R if r[4] == "T")
bytx = C.defaultdict(list)
for r in T: bytx[(r[2], r[3])].append(r)
buys = {}; moves = C.defaultdict(list); pools_of = C.defaultdict(set)
for (h, tok), rs in bytx.items():
    p = byt[tok]; pair = p["pool"].lower(); net = C.Counter()
    for r in rs: net[r[5]] -= r[7]; net[r[6]] += r[7]
    for a, v in net.items():
        if a in (pair,) or a in DEAD: continue
        if v > 0 and net[pair] < 0:
            buys.setdefault((tok, a), (rs[0][0], h)); pools_of[a].add(tok)
        elif v < 0:
            moves[(tok, a)].append((rs[0][0], "sell" if net[pair] > 0 else "transfer", h))
crowd = set(json.load(open(os.path.join(D, "d10_table.json")))["crowd"])
frozen_any = set(k[1] for k in fz)
wk_crowd = {a for a, s in pools_of.items() if len(s) >= 20 and a not in frozen_any}
BOTS = {"0x426603bac5e0ea73fd13aecad7a80c9f963f6eac", "0x8737a10d9c19af8bb2eae0b5e9cfe7b7276e0638", "0x220794f72f4b079a1d32469a3dffeda26b8651d8"}
cs = crowd | wk_crowd
rows = []
for (tok, a), (blk, h) in buys.items():
    p = byt[tok]; off = blk - p["launch_block"]
    if a in cs or a in BOTS or off >= 990 or a == p["pool"].lower(): continue
    z = fz.get((tok, a)); mv = [m for m in moves.get((tok, a), []) if m[0] >= blk and m[2] != h]
    pre = [m for m in mv if z is None or m[0] <= z[0]]
    rows.append({"token": tok, "buyer": a, "pool": p["pool"], "size": p["value"], "utc": p["launch_utc"], "off": off, "frozen": z is not None,
                 "freeze_off": (z[0] - p["launch_block"]) if z else None, "delay": (z[0] - blk) if z else None, "moves": len(mv), "moved_before_freeze": len(pre),
                 "first_move": (mv[0][0] - blk, mv[0][1]) if mv else None})
DEADA = "000000000000000000000000000000000000dead".rjust(64, "0")
bals = rpc.batch([("eth_call", [{"to": r["token"], "data": "0x70a08231" + r["buyer"][2:].rjust(64, "0")}, "latest"]) for r in rows])
for r, b in zip(rows, bals): r["bal_now"] = int(b["result"], 16) if b.get("result") not in (None, "0x") and "error" not in b else None
tk = [r for r in rows if r["bal_now"]]
res = rpc.batch([("eth_call", [{"from": r["buyer"], "to": r["token"], "gas": hex(300000), "data": "0xa9059cbb" + DEADA + hex(max(1, r["bal_now"] // 100))[2:].rjust(64, "0")}, "latest"]) for r in tk])
for r, x in zip(tk, res): r["test_now"] = "ok" if x.get("result") is not None and "error" not in x else "revert"
for r in rows: r.setdefault("test_now", "no balance")
def cls(r):
    if r["frozen"]: return "frozen, moved out first" if r["moved_before_freeze"] else "frozen while holding"
    return "never frozen, moved out" if r["moves"] else "never frozen, holding"
print("week crowd wallets (>=20 pools, never frozen):", len(wk_crowd), "of which in d10's crowd:", len(wk_crowd & crowd))
print("census-era strangers bought before +990:", len(rows), C.Counter(cls(r) for r in rows))
print("today's test by class:", sorted(C.Counter((cls(r), r["test_now"]) for r in rows).items()))
for r in sorted(rows, key=lambda r: r["off"]):
    if cls(r) != "frozen while holding": print("  ", cls(r), r["buyer"][:10], r["utc"], "size", r["size"], "buy +%d" % r["off"], "first move", r["first_move"], "freeze +%s" % r["freeze_off"], r["test_now"])
json.dump(rows, open(os.path.join(D, "d11b_census_strangers.json"), "w"), indent=0)
