"""Step 17: the hooked sibling shape (the watch's two 600-swap pools): every direct 196-byte PoolManager.initialize in the same 24.5 h with
an ETH pair, fee 500, tick spacing 1 and a hook; per pool the add, the pull, swaps to +600, routers, wallets, and the wallets'
overlap with the no-hook fleet."""
import collections
from common import *
d = jload("s01_inits.json"); start, head = d["start"], jload("s02_head.json")["head"]
fleet = {s["f"] for p in load_pools() for s in p["swaps"] if s["k"] == "fleet"}
ls = []
a = start
while a <= head:
    b = min(a + 49999, head); ls += rpc.logs({"address": PM, "topics": [T_INIT, None, ZERO32]}, a, b); a = b + 1
cand = []
for l in ls:
    dd = l["data"]; fee, ts, hook = W(dd, 0), sgn(W(dd, 1)), "0x" + dd[2 + 128 + 24: 2 + 192]
    if fee == 500 and ts == 1 and int(hook, 16) != 0: cand.append((l, hook))
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l, _ in cand], n=25)
pools = []
for (l, hook), t in zip(cand, txs):
    if (t.get("to") or "").lower() == PM and (len(t["input"]) - 2) // 2 == 196:
        pools.append(dict(pid=l["topics"][1], L=int(l["blockNumber"], 16), hook=hook, launcher=t["from"].lower(), nonce=int(t["nonce"], 16),
                          token="0x" + l["topics"][3][-40:], tick0=sgn(W(l["data"], 4))))
print("ETH-pair fee-500 ts-1 inits with a hook:", len(cand), "| direct 196-byte:", len(pools), "| hooks:", collections.Counter(p["hook"] for p in pools).most_common(5))
res = []
for p in pools:
    ev = []
    a = p["L"]
    while a <= head:
        b = min(a + 49999, head); ev += rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"]]]}, a, b); a = b + 1
    ml = [(int(e["blockNumber"], 16) - p["L"], ml_fields(e)) for e in ev if e["topics"][0] == T_ML]
    sw = [e for e in ev if e["topics"][0] == T_SWAP and int(e["blockNumber"], 16) <= p["L"] + 600]
    tx6 = rpc.batch("eth_getTransactionByHash", [[e["transactionHash"]] for e in sw], n=25)
    routers = collections.Counter(t["to"][:10] for t in tx6); wal = {t["from"].lower() for t in tx6}
    ein = sum(max(0, -swap_fields(e)["a0"]) for e in sw) / 1e18; eout = sum(max(0, swap_fields(e)["a0"]) for e in sw) / 1e18
    pulls = [o for o, m in ml if m["dl"] < 0]
    r = dict(L=p["L"], launcher=p["launcher"][:10], nonce=p["nonce"], hook=p["hook"], adds=[(o, m["tl"], m["tu"], f"{m['dl']:.3e}") for o, m in ml if m["dl"] > 0],
             pull=pulls[0] if pulls else None, n600=len(sw), first=(int(sw[0]["blockNumber"], 16) - p["L"]) if sw else None, ein600=round(ein, 3), eout600=round(eout, 3),
             routers=routers.most_common(3), wallets=len(wal), overlap_fleet=len(wal & fleet), n_all=sum(1 for e in ev if e["topics"][0] == T_SWAP))
    print(r)
    res.append(r)
jdump(res, "s17_hooked.json")
print(rpc.STATS)
