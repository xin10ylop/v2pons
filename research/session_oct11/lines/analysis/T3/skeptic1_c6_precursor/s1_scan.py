"""Skeptic 1, candidate 6 (the precursor angle: 'no transaction type holds a stable 1-4 block lead to T'). Stage 1, on a slice the finder never
used: the 12 hours BEFORE the precursor angle's window (its pools start at block 85734703), blocks 85311700..85734702 (Oct 10 21:24 -> Oct 11
09:38 UTC). Independently re-scanned: every Initialize on the PoolManager, its transaction (tx cache seeded read-only from the sibling skeptic's
cache of the same public-RPC answers), every 1,444-byte PositionManager launch (any value = any line), the 3.0 pools (value 3.0, fee 10000,
spacing 200, ETH pair, no hook, the line's price), the Swap / ModifyLiquidity logs of EVERY 1,444-byte pool to L+400, the transactions of
every 3.0 swap to L+120 and every liquidity call, and every log emitted by each 3.0 pool's token in [L, L+120]. -> pools.json
Read-only, public RPC only."""
import sys, json, collections, os
from lib import *
START, END = 85311700, 85734702
kv_tx = KV("tx"); print("tx cache: seeded", kv_tx.seeded, "own", len(kv_tx.d) - kv_tx.seeded, flush=True)
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
fn = "init_logs.json"
if os.path.exists(fn): ini = json.load(open(fn))
else:
    ini = []
    for a in range(START, END + 1, 20000):
        ini += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 19999, END))
    json.dump(ini, open(fn, "w"))
b0 = rpc("eth_getBlockByNumber", [hex(START), False]); b1 = rpc("eth_getBlockByNumber", [hex(END), False])
t0, t1 = int(b0["timestamp"], 16), int(b1["timestamp"], 16)
print(f"slice {START}..{END}: {utc(t0)} -> {utc(t1)} UTC, {(END-START)/(t1-t0):.2f} blocks/s; Initialize logs {len(ini)}", flush=True)
txs = gettx([l["transactionHash"] for l in ini])
launches = []; vals = collections.Counter()
for l, t in zip(ini, txs):
    if not t: print("  missing tx", l["transactionHash"]); continue
    clen = (len(t["input"]) - 2) // 2; to = (t.get("to") or "").lower(); v = int(t["value"], 16)
    if not (to == POSM and clen == 1444): continue
    line = "3.0" if v == 3 * 10 ** 18 else f"v{v/1e18:g}"
    is30 = (line == "3.0" and int(l["topics"][2], 16) == 0 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30)
    if line == "3.0" and not is30: print("  3.0-valued 1444-byte launch of another shape", l["transactionHash"]); line = "3.0x"
    vals[line] += 1
    launches.append({"line": line, "pid": l["topics"][1].lower(), "token": ("0x" + l["topics"][3][-40:]).lower(), "c0": ("0x" + l["topics"][2][-40:]).lower(),
                     "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16), "launch_tx": l["transactionHash"], "launcher": t["from"].lower(),
                     "launcher_nonce": int(t["nonce"], 16), "value": v})
launches.sort(key=lambda p: (p["L"], p["lti"]))
print("1444-byte PositionManager launches:", len(launches), dict(vals.most_common(12)), flush=True)
# Swap / ModifyLiquidity of every 1444-byte pool to L+400
ev = collections.defaultdict(list)
for i in range(0, len(launches), 20):
    g = launches[i:i + 20]; a = g[0]["L"]; b = g[-1]["L"] + 400
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b):
        ev[l["topics"][1].lower()].append(l)
    if (i // 20) % 5 == 0: print(f"  events {i + len(g)}/{len(launches)}", flush=True)
for p in launches:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
P30 = [p for p in launches if p["line"] == "3.0"]
need = [e["tx"] for p in P30 for e in p["ev"] if (e["kind"] == "ml" or e["bn"] <= p["L"] + 120)]
print("3.0 pools", len(P30), "swap/ml txs to fetch:", len(set(need) - set(kv_tx.d)), flush=True)
gettx(need)
# every log of each 3.0 pool's token in [L, L+120] (Transfer / Approval / anything) -> who touched the token before T
tl = collections.defaultdict(list)
for i in range(0, len(P30), 20):
    g = P30[i:i + 20]
    for l in logs({"address": [p["token"] for p in g]}, g[0]["L"], g[-1]["L"] + 120):
        tl[l["address"].lower()].append({"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
                                         "t": l["topics"], "d": l["data"]})
    if (i // 20) % 5 == 0: print(f"  token logs {i + len(g)}/{len(P30)}", flush=True)
for p in P30: p["tlogs"] = [x for x in tl[p["token"]] if p["L"] <= x["bn"] <= p["L"] + 120]
json.dump({"start": START, "end": END, "t0": t0, "t1": t1, "launches": launches}, open("pools.json", "w"))
print("done", flush=True)
