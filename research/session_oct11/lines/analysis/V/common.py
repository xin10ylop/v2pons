"""Verifier V: shared paths and helpers (read-only on the census and the repository)."""
import sys, os, json, math, statistics as st, collections as C
sys.dont_write_bytecode = True
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
V = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/v2pons"
sys.path.insert(0, CEN); sys.path.insert(0, os.path.join(CEN, "code")); sys.path.insert(0, os.path.join(REPO, "src"))
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
BOT = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"     # full address checked in v02 (event sender)
OURS = {"0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8", "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"}
ZERO = "0x" + "0" * 40
ETH_USD = 2570.0
T0 = 1791121962  # window start ts (Oct 4 13:52:42 UTC); day d = [T0 + 86400 d, T0 + 86400 (d+1))
def day_of(ts): return int((ts - T0) // 86400)
def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q; f = math.floor(k); c = math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)
def p3(xs): return tuple(None if pct(xs, q) is None else round(pct(xs, q), 4) for q in (0.1, 0.5, 0.9))
def jl(path):
    with open(path) as f:
        for line in f: yield json.loads(line)
