"""family-level statistics on the grid arrays (shared by g06/g07/g08)"""
from common import *
import numpy as np, gsim2 as gsim
KS = np.array(gsim.KS)

def load_grid(q):
    z = np.load(os.path.join(G, f"grid_q{q}.npz"))
    pools = list(z["pools"]); ix = {p: i for i, p in enumerate(pools)}
    return {"ix": ix, "skips": z["skips"], "raw": z["raw"], "S": z["S"], "pull_off": z["pull_off"], "q": q}

def fam_returns(grid, pools, conservative=False):
    """-> ret (n, 18, 143) with NaN = no trade, pulled (n, 18, 143) bool, sellat (n,18,143) offset from L"""
    idx = np.array([grid["ix"][p] for p in pools])
    raw = grid["raw"][idx]; S = grid["S"][idx].astype(np.int32); sk = grid["skips"][idx]; po = grid["pull_off"][idx]
    sell_off = KS[None, :, None] + S
    pulled = (po[:, None, None] <= sell_off) if conservative else (po[:, None, None] < sell_off)
    pullret = -1.0 - (0.02 / ETH_USD) / grid["q"]
    ret = np.where(pulled, pullret, raw).astype(np.float64)
    ret[sk != 0] = np.nan
    pulled = pulled & (sk[:, :, None] == 0)
    return ret, pulled, sell_off

def agg(ret, mask):
    """mean, count, sum over the pools in mask -> (18,143) arrays"""
    r = ret[mask]
    cnt = np.sum(~np.isnan(r), axis=0)
    s = np.nansum(r, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return mean, cnt, s

def one(ret_vec, pulled_vec):
    m = ~np.isnan(ret_vec); r = ret_vec[m]
    if len(r) == 0: return {"n": 0}
    return {"n": int(len(r)), "mean": float(r.mean()), "median": float(np.median(r)), "win": float((r > 0).mean()), "worst": float(r.min()),
            "best": float(r.max()), "pulled": float(pulled_vec[m].mean()), "usd_per_trade": None}
