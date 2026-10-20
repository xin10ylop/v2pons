"""run the full rule grid on every pool of every kept family: q (ETH) from argv (default 0.0058) -> grid_q<q>.npz
arrays: pools (N), skips (N, 18) int8, raw (N, 18, 143) float32 = value of the sale as a return on q net of gas (no pull accounting),
S (N, 18, 143) int16 = the sell block offset after our buy, pull_off (N) = first pull block - L (9999 = none), n_ours (N)"""
from common import *
import numpy as np, multiprocessing as mp, time, gsim2 as gsim
Q = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0058
ONLY = sys.argv[2] if len(sys.argv) > 2 else None        # optional: a json list of family keys to restrict to
rows = {r["pool"]: r for r in load_rows()}
EV = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
kept = json.load(open(os.path.join(G, "families_kept.json")))
if ONLY: kept = {k: v for k, v in kept.items() if k in set(json.load(open(ONLY)))}
pools = sorted(set(p for v in kept.values() for p in v), key=lambda p: rows[p]["launch_block"])

def work(p):
    ps = gsim.PoolSim(rows[p], EV[p])
    sk, raw, S = ps.grid(Q)
    return sk, raw, S, (ps.pull_bn - ps.L) if ps.pull_bn is not None else 9999, ps.n_ours

if __name__ == "__main__":
    t = time.time()
    with mp.Pool(4) as pool:
        res = pool.map(work, pools, chunksize=200)
    out = os.path.join(G, f"grid_q{Q}.npz")
    np.savez(out, pools=np.array(pools), skips=np.array([r[0] for r in res]), raw=np.array([r[1] for r in res]),
             S=np.array([r[2] for r in res]), pull_off=np.array([r[3] for r in res]), n_ours=np.array([r[4] for r in res]))
    print(len(pools), "pools", f"{time.time()-t:.0f}s ->", out)
