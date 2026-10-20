"""Siblings of the four shapes in the same 12 h (from the s01 caches): launches by the same selectors (7fde822e, a25a9a3d, 7866fa39) or the same
hooks (0x4e346895.., 0x2c668601..) through other targets; their Swaps (any time to the head) and liquidity removals; plus the code size of the
S2 position-NFT holder 0x7baab0ac. Cache: cache/s10_ev_cache.jsonl. Prints s10_siblings.out."""
from common import *
import rpc, collections
X = json.load(open(J("s01_launches.json"))); core = {r["pid"] for v in X.values() for r in v}
TX = {t["hash"]: t for t in jl(C("s01_txs_cache.jsonl"))}
head = json.load(open(J("s05_head.json")))["head"]
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
H1, H2 = "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544", "0x2c668601193e4a081dd82604785e436aff6a2acc"
sib = []
for l in jl(C("s01_inits_cache.jsonl")):
    t = TX.get(l["transactionHash"])
    if not t or l["topics"][1] in core: continue
    hk = "0x%040x" % W(l["data"], 2); sel = t["input"][2:10]
    if sel in ("7fde822e", "a25a9a3d", "7866fa39") or hk in (H1, H2):
        sib.append({"pid": l["topics"][1], "ltx": l["transactionHash"], "lb": int(l["blockNumber"], 16), "to": t["to"], "sel": sel, "n": (len(t["input"]) - 2) // 2, "from": t["from"], "hook": hk,
                    "c0": "0x" + l["topics"][2][-40:]})
print(len(sib), "sibling launches")
for k, c in collections.Counter((s["sel"], s["hook"][:10], s["to"][:10]) for s in sib).most_common(20): print("   ", c, k, "wallets", len({s["from"] for s in sib if (s["sel"], s["hook"][:10], s["to"][:10]) == k}))
ev = jl(C("s10_ev_cache.jsonl"))
if not ev and sib:
    ids = sorted({s["pid"] for s in sib}); a = min(s["lb"] for s in sib)
    with open(C("s10_ev_cache.jsonl"), "w") as f:
        for b0 in range(a, head + 1, 50_000):
            for i in range(0, len(ids), 100):
                for l in rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], ids[i:i + 100]]}, b0, min(b0 + 49_999, head)):
                    ev.append(l); f.write(json.dumps(l) + "\n")
lb = {s["pid"]: s for s in sib}
txs = {t["hash"]: t for t in jl(C("s10_tx_cache.jsonl"))}
need = sorted({l["transactionHash"] for l in ev if l["topics"][0] == T_SWAP} - set(txs))
with open(C("s10_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for t in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20):
            if t: t = {k: t[k] for k in ("hash", "from", "to", "value")} | {"sel": t["input"][2:10]}; txs[t["hash"]] = t; f.write(json.dumps(t) + "\n")
grp = collections.defaultdict(lambda: {"pools": set(), "swapped": set(), "ext": set(), "ext600": set(), "pulled": set(), "ext_eth": 0.0})
for s in sib: grp[(s["sel"], s["hook"][:10])]["pools"].add(s["pid"])
for l in ev:
    s = lb[l["topics"][1]]; g = grp[(s["sel"], s["hook"][:10])]; bn = int(l["blockNumber"], 16)
    if l["topics"][0] == T_ML:
        if sgn(W(l["data"], 2)) < 0: g["pulled"].add(s["pid"])
        continue
    t = txs.get(l["transactionHash"], {}); fr = t.get("from")
    if l["transactionHash"] == s["ltx"]: continue
    g["swapped"].add(s["pid"])
    if fr and fr not in (SENT, s["from"]):
        a0 = sgn(W(l["data"], 0)); g["ext"].add(s["pid"])
        if bn - s["lb"] <= 600: g["ext600"].add(s["pid"])
        if s["c0"] in ("0x" + "0" * 40, WETH) and a0 < 0: g["ext_eth"] += -a0 / 1e18
for k, g in grp.items():
    print(f"  {k}: pools {len(g['pools'])}, with any swap {len(g['swapped'])}, with an outside (not sentinel, not launcher) swap {len(g['ext'])} "
          f"(within +600: {len(g['ext600'])}), outside ETH/WETH bought {g['ext_eth']:.4f}, liquidity removed in {len(g['pulled'])}")
print("outside swaps of the hooked siblings (pool, offset, side, quote amount in 1e-18 units, from, to:sel):")
for l in sorted(ev, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
    s = lb[l["topics"][1]]
    if l["topics"][0] != T_SWAP or s["sel"] == "7fde822e" or l["transactionHash"] == s["ltx"]: continue
    t = txs.get(l["transactionHash"], {})
    if t.get("from") in (SENT, s["from"]): continue
    a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1)); q0 = s["c0"] in ("0x" + "0" * 40, WETH, "0x5fc5360d0400a0fd4f2af552add042d716f1d168", "0x4a0e65a3eccec6dbe60ae065f2e7bb85fae35eea")
    aq = a0 if q0 else a1
    print(f"   {s['sel']} {l['topics'][1][:10]} quote {(s['c0'] if q0 else '(c1)')[:10]} +{int(l['blockNumber'], 16) - s['lb']:<6d} {'BUY ' if aq < 0 else 'SELL'} {abs(aq):.4g} {t.get('from', '?')[:10]} {(t.get('to') or '')[:10]}:{t.get('sel')}")
c = rpc.call("eth_getCode", ["0x7baab0acf4f27f719996e6c64151bdd9007b8464", "latest"]); print("S2 NFT holder 0x7baab0ac code", len(c) // 2 - 1, "B")
print(rpc.STATS)
