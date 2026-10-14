"""d02: the logs of every launch of d01. (a) every Transfer of every token from its launch block to the head (buys, sells, transfers);
(b) every Swap, Sync, Mint, Burn of every pair from L to L+8000 (or the head). eth_getLogs with address arrays in 5,000-block chunks on
keyless archive endpoints (sentio, blockmachine, pocket). Compact records, resumable:
  cache/d02_transfers_cache.jsonl   [blk, txi, li, tx, token, from, to, value]
  cache/d02_pairlogs_cache.jsonl    [blk, txi, li, tx, pair, kind, data words...]
  cache/d02_done_cache.jsonl        chunks done"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rpc
D = os.path.dirname(os.path.abspath(__file__)); C = os.path.join(D, "cache")
TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
K = {"0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1": "sync", "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822": "swap",
     "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f": "mint", "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496": "burn"}
d = json.load(open(os.path.join(D, "d01_launches.json"))); L = d["launches"]
head = int(rpc.call("eth_blockNumber", []), 16) if len(sys.argv) < 2 else int(sys.argv[1])
FROM = min(o["L"] for o in L); STEP = 5000; G = 120; PW = 8000
done = set()
fd = os.path.join(C, "d02_done_cache.jsonl")
if os.path.exists(fd):
    for ln in open(fd): done.add(tuple(json.loads(ln)))
ft = open(os.path.join(C, "d02_transfers_cache.jsonl"), "a"); fp = open(os.path.join(C, "d02_pairlogs_cache.jsonl"), "a"); fdn = open(fd, "a")
def w(x): return [x[i:i + 64] for i in range(0, len(x), 64)]
x = FROM; nt = npl = 0
while x <= head:
    e = min(head, x + STEP - 1)
    if ("c", x, e) in done: x = e + 1; continue
    toks = sorted(o["token"] for o in L if o["L"] <= e)
    pairs = sorted(o["pair"] for o in L if o["L"] <= e and o["L"] + PW >= x)
    out_t, out_p = [], []
    for i in range(0, len(toks), G):
        for lg in rpc.logs({"address": toks[i:i + G], "topics": [TT]}, x, e, step=STEP):
            if len(lg["topics"]) < 3: continue
            out_t.append([int(lg["blockNumber"], 16), int(lg["transactionIndex"], 16), int(lg["logIndex"], 16), lg["transactionHash"], lg["address"].lower(),
                          "0x" + lg["topics"][1][-40:], "0x" + lg["topics"][2][-40:], int(lg["data"][2:66] or "0", 16)])
    for i in range(0, len(pairs), G):
        for lg in rpc.logs({"address": pairs[i:i + G], "topics": [list(K)]}, x, e, step=STEP):
            k = K[lg["topics"][0]]; ws = [int(v, 16) for v in w(lg["data"][2:])]
            rec = [int(lg["blockNumber"], 16), int(lg["transactionIndex"], 16), int(lg["logIndex"], 16), lg["transactionHash"], lg["address"].lower(), k] + ws
            if k in ("swap", "mint", "burn"): rec.append("0x" + lg["topics"][1][-40:])
            if k in ("swap", "burn"): rec.append("0x" + lg["topics"][2][-40:])
            out_p.append(rec)
    for r in out_t: ft.write(json.dumps(r) + "\n")
    for r in out_p: fp.write(json.dumps(r) + "\n")
    ft.flush(); fp.flush(); fdn.write(json.dumps(["c", x, e]) + "\n"); fdn.flush()
    nt += len(out_t); npl += len(out_p)
    if (x - FROM) // STEP % 10 == 0: print("chunk", x, e, "tokens", len(toks), "pairs", len(pairs), "transfers", nt, "pairlogs", npl, rpc.STATS, flush=True)
    x = e + 1
print("done to head", head, "transfers", nt, "pairlogs", npl)
