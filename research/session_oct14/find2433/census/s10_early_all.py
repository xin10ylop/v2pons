"""Step 10: shape-blind check. The swaps in [L, L+30] of EVERY launch except S1/S2 (coin-factory hooks) and VB 3.0/5.0 (sampled in s05),
to find any actor that buys early and big across many new pools whatever their shape. Resumable; s10_early_cache.jsonl rows {pid, sw:[...]}."""
from common import *
W30 = 30
rows = jload("s04_launches.json")
SKIP = {"S1 coin factory hook 0x4e346895", "S2 lift.fun 7866fa39", "VB 3.0", "VB 5.0"}
done = {r["pid"] for r in jl_load("s10_early_cache.jsonl")} | {r["pid"] for r in jl_load("s05_events_cache.jsonl")}
todo = [r for r in rows if r["fam"] not in SKIP and r["pid"] not in done]
print("todo", len(todo), flush=True)
for i in range(0, len(todo), 100):
    ch = todo[i:i + 100]
    qs = []
    for r in ch:
        if r["ven"] == "v4": qs.append([{"address": PM, "topics": [T_SWAP, r["pid"]], "fromBlock": hex(r["b"]), "toBlock": hex(r["b"] + W30)}])
        else: qs.append([{"address": r["pid"], "topics": [T_V3SWAP], "fromBlock": hex(r["b"]), "toBlock": hex(r["b"] + W30)}])
    res = rpc.batch("eth_getLogs", qs, n=20)
    out = []
    for r, ls in zip(ch, res):
        if ls is None: continue
        out.append(dict(pid=r["pid"], ven=r["ven"], L=r["b"], sw=[[int(l["blockNumber"], 16), int(l["transactionIndex"], 16), int(l["logIndex"], 16), l["transactionHash"],
                         "0x" + l["topics"][2][-40:] if len(l["topics"]) > 2 else "", l["data"]] + (["0x" + l["topics"][1][-40:]] if r["ven"] == "v3" else []) for l in ls]))
    jl_append(out, "s10_early_cache.jsonl")
    print(i + len(ch), "/", len(todo), rpc.STATS, flush=True)
