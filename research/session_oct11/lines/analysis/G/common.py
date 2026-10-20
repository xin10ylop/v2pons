"""analyst G (grid): shared helpers"""
import os, sys, json, math, pickle, collections as C, statistics as S
G = os.path.dirname(os.path.abspath(__file__))
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
FROM_TS = 1791121962            # Oct 4 13:52:42 UTC (window start)
END_TS = FROM_TS + 7 * 86400    # Oct 11 13:52:42
FIT_END = FROM_TS + 5 * 86400   # days 1-5 = fit, days 6-7 = validation
LAST48 = END_TS - 2 * 86400
LAST24 = END_TS - 86400
ETH_USD = 2570.0
OUR_WALLET = "0xab5a34c3"
OUR_RELAY = "0x2abb5653"
ZERO = "0x0000000000000000000000000000000000000000"

def day(ts): return min(6, max(0, int((ts - FROM_TS) // 86400)))
def slice6(ts): return min(27, max(0, int((ts - FROM_TS) // 21600)))

def shape_key(r):
    l = r["launch"]
    tgt = l["target"] if l.get("to") else "create:" + (l.get("target_code_hash") or "none")[:16]
    val = "%.7f" % (int(l["value_wei"]) / 1e18)
    hz = "nohook" if r["hooks"] == ZERO else "hook"
    return f"{tgt}|{l['selector']}|{l['calldata_len']}|{r['fee']}|{r['tick_spacing']}|{hz}|{r['quote']}|{val}"

def tok_key(r): return "tok:" + (r["fam"].get("tok") or "none")

def load_rows():
    return pickle.load(open(os.path.join(G, "v4rows.pkl"), "rb"))

def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)
