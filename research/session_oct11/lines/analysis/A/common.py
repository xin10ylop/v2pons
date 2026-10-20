"""Shared loading for analyst A: the non-vbot rows of lc:c873e135|ac9650d8 with their events and per-pool launch shape."""
import json, os, sys, pickle, collections as C, statistics as S
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
sys.path.insert(0, CEN); sys.path.insert(0, os.path.join(CEN, "code")); sys.path.insert(0, "/home/user/v2pons/src")
OUT = os.path.dirname(os.path.abspath(__file__))
VB = {"vbot-v2.433", "vbot-v3.0", "vbot-v5.0"}; VBV = {2433328500000000000, 2433300000000000000, 3 * 10**18, 5 * 10**18}
T0 = 1791121962  # window start 2026-10-04 13:52:42 UTC (launch_ts of block 79,984,897 approx)
HEAD_TS = T0 + 7 * 86400


def all_rows():
    return [json.loads(l) for l in open(os.path.join(OUT, "lc_rows.jsonl"))]


def is_vbot(r):
    return r["known_fp"] in VB or r["launch"]["value_wei"] in VBV


def rows_nonvbot():
    return [r for r in all_rows() if not r["quote_pair"] and not is_vbot(r)]


def load_ev():
    return pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))


def mint_info(r, o):
    """liquidity adds in the launch tx (v4 'm' rows with delta > 0): total L, number of positions, ranges"""
    adds = [e for e in o["ev"] if e[0] == "m" and e[8] > 0 and e[10] == r["launch_tx"]]
    return sum(e[8] for e in adds), len(adds), tuple(sorted((e[6], e[7]) for e in adds))


def day_of(r):
    """day index 0..6 from the window start"""
    return min(6, max(0, int((r["launch_ts"] - T0) // 86400)))


def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def p1050(xs):
    return [None if not xs else round(pct(xs, q), 4) for q in (0.1, 0.5, 0.9)]
