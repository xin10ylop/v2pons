"""p03: every launch by a launcher with code keccak 89885b75... over the 48 hours (p01, p02), decoded: the call (d27d1e00's words: token,
an address, an ETH amount, an address, two dynamic arrays: addresses[] and uint[]), and the receipt (pools created, Initialize, Mints,
the launch-tx Swaps, the token Transfers to the array's addresses). Offline. -> p03_launches.json, p03_launches.out"""
import sys, os, json, time, bisect, collections as C, statistics as S
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
J = lambda n: os.path.join(HERE, n)
CODE89 = "89885b75fd29af130416accacb0351226a4259b3090dc0a2bb56189489efe08a"
WETH = "0bd7d308f8e1639fab988df18a8011f41eacad73"; FACTORY = "1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "73991a25c818bf1f1128deaab1492d45638de0d3"
T = {"created": "783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118", "init": "98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95",
     "mint": "7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde", "swap": "c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67",
     "burn": "0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c", "incr": "3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f",
     "transfer": "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef", "deposit": "e1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c",
     "withdrawal": "7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"}
LINE_L = 31_622_807_953_636_212_567_716
meta = json.load(open(J("p01_meta.json")))
G = sorted((int(k), v) for k, v in meta["grid"].items()); GB = [g[0] for g in G]
def ts(b):
    i = min(max(0, bisect.bisect_right(GB, b) - 1), len(G) - 2); (b0, t0), (b1, t1) = G[i], G[i + 1]; return t0 + (b - b0) * (t1 - t0) / (b1 - b0)
def u(h, i): return int(h[64 * i:64 * i + 64], 16)
def s(x): return x - (1 << 256) if x >> 255 else x
rows = [json.loads(x) for x in open(J("p01_pools.jsonl"))]
tx = {}
for x in open(J("p01_txs.jsonl")):
    t = json.loads(x); tx[t["hash"]] = t
code = json.load(open(J("p01_code.json")))
rc = {}
for x in open(J("p02_receipts.jsonl")):
    r = json.loads(x); rc[r["transactionHash"]] = r
L89 = sorted(set(r["tx"] for r in rows if code.get((tx[r["tx"]]["to"] or "").lower(), {}).get("hash") == CODE89), key=lambda h: int(tx[h]["blockNumber"], 16))
out = []; P = []
def p(*a):
    P.append(" ".join(str(x) for x in a)); print(*a)
for h in L89:
    t = tx[h]; r = rc[h]; d = t["input"][10:]; n = (len(d)) // 64
    call = {"token": d[24:64], "a1": d[64 + 24:128], "eth2": u(d, 2), "a3": d[3 * 64 + 24:4 * 64], "w6": u(d, 6), "a7": d[7 * 64 + 24:8 * 64], "w8": u(d, 8)}
    o1, o2 = u(d, 4) // 32, u(d, 5) // 32
    n1 = u(d, o1); addrs = [d[64 * (o1 + 1 + i) + 24:64 * (o1 + 2 + i)] for i in range(n1)]
    n2 = u(d, o2); amts = [u(d, o2 + 1 + i) for i in range(n2)]
    call.update({"n_addrs": n1, "addrs": addrs, "n_amts": n2, "amts": amts, "sum_amts": sum(amts), "words": n, "arr_offsets": [u(d, 4), u(d, 5)]})
    logs = r["logs"]; A = lambda l: l["address"][2:].lower(); t0 = lambda l: l["topics"][0][2:]
    created = [l for l in logs if A(l) == FACTORY and t0(l) == T["created"]]
    pools = [l["data"][2 + 64 + 24:2 + 128] for l in created]
    pool = pools[0] if pools else None
    inits = [(u(l["data"][2:], 0), s(u(l["data"][2:], 1))) for l in logs if A(l) in pools and t0(l) == T["init"]]
    mints = [{"pool": A(l), "owner": l["topics"][2][-40:] if False else l["topics"][1][-40:], "lo": s(int(l["topics"][2], 16)), "hi": s(int(l["topics"][3], 16)),
              "sender": l["data"][2 + 24:2 + 64], "L": u(l["data"][2:], 1), "a0": u(l["data"][2:], 2), "a1": u(l["data"][2:], 3)} for l in logs if A(l) in pools and t0(l) == T["mint"]]
    swaps = [{"pool": A(l), "sender": l["topics"][1][-40:], "rcpt": l["topics"][2][-40:], "a0": s(u(l["data"][2:], 0)), "a1": s(u(l["data"][2:], 1)),
              "sqrtP": u(l["data"][2:], 2), "liq": u(l["data"][2:], 3), "tick": s(u(l["data"][2:], 4)), "li": int(l["logIndex"], 16)} for l in logs if A(l) in pools and t0(l) == T["swap"]]
    tok = call["token"]
    tr = [(l["topics"][1][-40:], l["topics"][2][-40:], int(l["data"], 16)) for l in logs if A(l) == tok and t0(l) == T["transfer"]]
    incr = [(int(l["topics"][1], 16), u(l["data"][2:], 0)) for l in logs if A(l) == NPM and t0(l) == T["incr"]]
    to_addrs = C.Counter()
    for f_, to_, v in tr:
        if to_ in addrs: to_addrs[to_] += v
    row = {"tx": h, "block": int(t["blockNumber"], 16), "ts": ts(int(t["blockNumber"], 16)), "from": t["from"][2:].lower(), "nonce": int(t["nonce"], 16), "to": t["to"][2:].lower(),
           "len": (len(t["input"]) - 2) // 2, "sel": t["input"][2:10], "value": int(t["value"], 16), "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "status": r["status"],
           "gasUsed": int(r["gasUsed"], 16), "call": call, "pools": pools, "pool": pool, "token": tok, "created": [(l["topics"][1][-40:], l["topics"][2][-40:], int(l["topics"][3], 16)) for l in created],
           "inits": inits, "mints": mints, "swaps": swaps, "incr": incr, "n_logs": len(logs), "tok_to_addrs": dict(to_addrs), "n_tok_transfers": len(tr),
           "from_in_addrs": t["from"][2:].lower() in addrs}
    out.append(row)
json.dump(out, open(J("p03_launches.json"), "w"))
# ------------------------------------------------------------------ tables
f = lambda x: time.strftime("%m-%d %H:%M", time.gmtime(x))
p(f"launches by launcher code 89885b75 in {f(meta['from_ts'])} .. {f(meta['head_ts'])} UTC: {len(out)}")
p("\nBY CALLDATA LENGTH (selector d27d1e00 in all): n | value ETH | array length | first | last")
by = C.defaultdict(list)
for x in out: by[x["len"]].append(x)
for L_, xs in sorted(by.items()):
    p(f"  {L_:5d} B n {len(xs):3d} | value {sorted(set(round(x['value']/1e18, 4) for x in xs))} | arrays {sorted(set((x['call']['n_addrs'], x['call']['n_amts']) for x in xs))} | {f(xs[0]['ts'])} .. {f(xs[-1]['ts'])}")
p("  check: 356 + 64*N == len for all? ", all(x["len"] == 356 + 64 * x["call"]["n_addrs"] and x["call"]["n_addrs"] == x["call"]["n_amts"] for x in out))
p("  check: value == eth2 + sum(amounts) for all? ", all(x["value"] == x["call"]["eth2"] + x["call"]["sum_amts"] for x in out),
  "| exceptions:", [(x["len"], x["value"] / 1e18, x["call"]["eth2"] / 1e18, x["call"]["sum_amts"] / 1e18) for x in out if x["value"] != x["call"]["eth2"] + x["call"]["sum_amts"]][:5])
p("  selectors:", C.Counter(x["sel"] for x in out), "| status:", C.Counter(x["status"] for x in out), "| prio:", C.Counter(x["prio"] for x in out))
p("\nBY HOUR (UTC): 356-B value 0 | other lengths (value > 0)")
hb = C.defaultdict(lambda: [0, 0])
for x in out: hb[int(x["ts"] // 3600)][0 if x["len"] == 356 else 1] += 1
for k in sorted(hb): p(f"  {time.strftime('%m-%d %H', time.gmtime(k*3600))}h  {hb[k][0]:3d} | {hb[k][1]:3d}")
p("\nRECEIPT SHAPE by kind (v0 = 356 B value 0; val = longer, value > 0)")
for lab, xs in (("v0", [x for x in out if x["len"] == 356]), ("val", [x for x in out if x["len"] != 356])):
    p(f" [{lab}] n {len(xs)}")
    p("   pools per tx:", C.Counter(len(x["pools"]) for x in xs), "| WETH token0:", sum(1 for x in xs if x["created"] and x["created"][0][0] == WETH), "| fee:", C.Counter(c[2] for x in xs for c in x["created"]))
    p("   Initialize tick:", C.Counter(i[1] for x in xs for i in x["inits"]).most_common(5))
    p("   mints per tx:", C.Counter(len(x["mints"]) for x in xs), "| (lo, hi):", C.Counter((m["lo"], m["hi"]) for x in xs for m in x["mints"]).most_common(5))
    p("   mint L == 31,622,807,953,636,212,567,716:", sum(1 for x in xs for m in x["mints"] if m["L"] == LINE_L), "of", sum(len(x["mints"]) for x in xs),
      "| other L:", C.Counter(m["L"] for x in xs for m in x["mints"] if m["L"] != LINE_L).most_common(4))
    p("   mint owner/sender = PositionManager:", sum(1 for x in xs for m in x["mints"] if m["owner"] == NPM and m["sender"] == NPM), "| amount0 (WETH) 0:", sum(1 for x in xs for m in x["mints"] if m["a0"] == 0),
      "| token amount1:", C.Counter(m["a1"] for x in xs for m in x["mints"]).most_common(3))
    p("   swaps in the launch tx per tx:", C.Counter(len(x["swaps"]) for x in xs), "| array length:", C.Counter(x["call"]["n_addrs"] for x in xs))
    sw = [x for x in xs if x["swaps"]]
    if sw:
        p("   swaps == array length:", sum(1 for x in sw if len(x["swaps"]) == x["call"]["n_addrs"]), "of", len(sw),
          "| every swap a buy (WETH in, amount0 > 0):", all(s_["a0"] > 0 for x in sw for s_ in x["swaps"]),
          "| swap WETH in == array amounts (in order):", sum(1 for x in sw if [s_["a0"] for s_ in sorted(x["swaps"], key=lambda z: z["li"])] == x["call"]["amts"]), "of", len(sw))
        p("   swap sender:", C.Counter(s_["sender"][:8] for x in sw for s_ in x["swaps"]).most_common(3), "| swap recipient == the array's address (in order):",
          sum(1 for x in sw if [s_["rcpt"] for s_ in sorted(x["swaps"], key=lambda z: z["li"])] == x["call"]["addrs"]), "of", len(sw))
        p("   launch-tx buy ETH per launch (sum of amounts) p10/p50/p90:", [round(q / 1e18, 2) for q in (sorted(x["call"]["sum_amts"] for x in sw)[len(sw) // 10], S.median(x["call"]["sum_amts"] for x in sw), sorted(x["call"]["sum_amts"] for x in sw)[9 * len(sw) // 10])])
        p("   tick after the launch-tx buys p10/p50/p90:", [sorted(x["swaps"][-1]["tick"] for x in sw)[i] for i in (len(sw) // 10, len(sw) // 2, 9 * len(sw) // 10)])
        p("   from (launch wallet) in the array:", sum(1 for x in sw if x["from_in_addrs"]), "of", len(sw), "| first array address == from:", sum(1 for x in sw if x["call"]["addrs"] and x["call"]["addrs"][0] == x["from"]))
    p("   eth2 (word 2) values:", C.Counter(round(x["call"]["eth2"] / 1e18, 4) for x in xs).most_common(8))
    p("   word1 == word3 == word7:", sum(1 for x in xs if x["call"]["a1"] == x["call"]["a3"] == x["call"]["a7"]), "| word6, word8 zero:", sum(1 for x in xs if x["call"]["w6"] == 0 and x["call"]["w8"] == 0))
    p("   launch wallets:", len(set(x["from"] for x in xs)), "| nonce p50:", S.median(x["nonce"] for x in xs), "| gasUsed p50:", S.median(x["gasUsed"] for x in xs))
open(J("p03_launches.out"), "w").write("\n".join(P) + "\n")
