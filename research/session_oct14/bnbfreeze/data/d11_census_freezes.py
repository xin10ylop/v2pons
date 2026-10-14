"""d11: did the freeze exist during REPORT_BNB's census (Oct 4-11)? The freeze-shaped logs (topic0 0x8c5be1e5...eeaa0, the token's approve)
of the 290 1/10/25-BNB pools of the research's family list (verify/execution_..._tok_9f0350.../out/e01_fam_pools.json), from the census
start to the research's head (125757132..127139740), and each token's Transfers from the pair, so every freeze has its target's buy.
-> cache/d11_census_cache.jsonl; d11_census_freezes.json; d11_census_freezes.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
RV = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/verify"
FP = json.load(open(RV + "/execution_PancakeSwap_V2_on_BNB_Chain__F_tok_9f0350f062d95ea48f746574ee0b7af7d643/out/e01_fam_pools.json"))
FRZ = "0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0"; TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
A0, A1 = 125757132, 127139740; STEP = 10000; G = 150
fn = os.path.join(CACHE, "d11_census_cache.jsonl")
if not os.path.exists(fn):
    f = open(fn, "w"); x = A0
    while x <= A1:
        e = min(A1, x + STEP - 1); toks = sorted(p["token"].lower() for p in FP if p["launch_block"] <= e)
        for i in range(0, len(toks), G):
            if not toks[i:i + G]: continue
            for lg in rpc.logs({"address": toks[i:i + G], "topics": [[FRZ, TT]]}, x, e, step=STEP):
                tp = lg["topics"] + [None] * 3
                f.write(json.dumps([int(lg["blockNumber"], 16), int(lg["transactionIndex"], 16), lg["transactionHash"], lg["address"].lower(), "F" if tp[0] == FRZ else "T",
                                    "0x" + tp[1][-40:], "0x" + tp[2][-40:], int(lg["data"][2:66] or "0", 16) if tp[0] == TT else 0]) + "\n")
        x = e + 1
    f.close()
R = [json.loads(l) for l in open(fn)]
byt = {p["token"].lower(): p for p in FP}
OPS = {"0x623e7c23c7c228095f94d9bd567eae55cb87a966", "0xa70b3f34e3ca7d4665b794ce6bb29168b1d2e40d", "0xbd418ce6a83995971de9f1cf9f61f345e91aeadd", "0xd604540564b6f659de163ad928e29782185da2fd"}
F = [r for r in R if r[4] == "F"]
print("census-era tokens", len(FP), "freeze-shaped logs", len(F), "callers (top):", C.Counter(r[5] for r in F).most_common(8))
fz = {}
for r in sorted(F):
    if r[6] != ROUTER and r[5] in OPS: fz.setdefault((r[3], r[6]), r)
first_buy = {}; outs = C.defaultdict(list)
for r in sorted(R):
    if r[4] != "T": continue
    p = byt[r[3]]; pair = p["pool"].lower()
    if r[5] == pair: first_buy.setdefault((r[3], r[6]), r)
    else: outs[(r[3], r[5])].append(r)
crowd = set(json.load(open(os.path.join(D, "d10_table.json")))["crowd"])
rows = []
for (tok, tgt), r in fz.items():
    p = byt[tok]; b = first_buy.get((tok, tgt))
    rows.append({"token": tok, "pool": p["pool"], "size": p["value"], "L": p["launch_block"], "utc": p["launch_utc"], "target": tgt, "crowd": tgt in crowd,
                 "op": r[5], "foff": r[0] - p["launch_block"], "buy_off": (b[0] - p["launch_block"]) if b else None, "delay": (r[0] - b[0]) if b else None})
print("operator freezes", len(rows), "first", min(rows, key=lambda r: r["L"] + r["foff"])["utc"] if rows else None, "per launch day:", sorted(C.Counter(r["utc"][:10] for r in rows).items()))
print("pools with >= 1 operator freeze:", len(set(r["pool"] for r in rows)), "of", len(FP), "| freezes of crowd wallets:", sum(r["crowd"] for r in rows))
dl = sorted(r["delay"] for r in rows if r["delay"] is not None and r["delay"] >= 0)
if dl: print("delay buy -> freeze: n", len(dl), "min", dl[0], "median", dl[len(dl) // 2], "p90", dl[int(.9 * len(dl))], "max", dl[-1])
# the research's 4 outsider round trips (e13) and the stranger buys (v04)
SELLERS = ["0xf4d846a1", "0x6951d193", "0xb1ce227d", "0x3b81a163"]
for s in SELLERS:
    for (tok, a), v in outs.items():
        if a.startswith(s):
            p = byt[tok]; b = first_buy.get((tok, a)); z = fz.get((tok, a))
            print("research outsider", a, "pool", p["pool"][:10], p["launch_utc"], "size", p["value"], "buy +%s" % ((b[0] - p["launch_block"]) if b else None),
                  "out +%s" % [x[0] - p["launch_block"] for x in v][:4], "to pair" if v[0][6] == p["pool"].lower() else "to " + v[0][6][:10],
                  "frozen +%s" % ((z[0] - p["launch_block"]) if z else None))
json.dump(rows, open(os.path.join(D, "d11_census_freezes.json"), "w"), indent=0)
