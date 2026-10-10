import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, ".")
from chain import T_SWAP, T_ML, W, sgn
from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
k = "create|60808060|3740|2500|25|true"; pids = F[k]["pids"]; E = load_events(set(pids))
cache = json.load(open("cache/postwindow_logs.json"))[k]
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
Ns = [3000, 5000, 10000, 20000, 50000, 100000, 300000]
res = {N: [] for N in Ns}; rows = []
for pid in pids:
    pl = Pool(P[pid], E.get(pid), T, M)
    ext = sorted([l for l in cache if l["topics"][1] == pid and l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) > pl.b0 + 3000],
                 key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    prev = pl.seq[-1]["sqrt_p"] if pl.seq else pl.s0
    big = []
    for l in ext:
        d = l["data"]; a0 = s128(W(d, 0)); sp = W(d, 2); liq = W(d, 3)
        x = {"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "a0": a0, "sqrt_p": sp, "liq": liq, "fee": W(d, 5), "buy": a0 < 0, "eth": abs(a0), "relay": False, "in_launch": False}
        if x["buy"]: x["d_inv"] = Q96 / sp - Q96 / prev
        else:
            x["d_sp"] = sp - prev
            if x["eth"] >= int(1e18): big.append((x["bn"] - pl.b0, round(x["eth"] / 1e18, 3)))
        prev = sp; pl.seq.append(x)
    row = {"pid": pid[:12], "dumps_after_window": big[:5]}
    for N in Ns:
        r = pl.trade(pl.b0 + 1, pl.b0 + N); res[N].append(r); row[N] = round(r["ret"], 3)
    rows.append(row); print(row)
summ = {N: summarize(res[N]) for N in Ns}
for N in Ns: s = summ[N]; print("hold +%d (%.0f min): n %d mean %+.3f median %+.3f win %.2f min %+.3f" % (N, N * 0.1026 / 60, s["n"], s["mean"], s["median"], s["win"], s["min"]))
json.dump({"rows": rows, "summary": summ}, open("fam4_long.json", "w"), indent=1)
