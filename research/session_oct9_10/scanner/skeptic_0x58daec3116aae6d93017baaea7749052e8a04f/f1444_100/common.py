import sys, json, os, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/home/user/v2pons/src")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import rpc, batch, logs, block_at, PM, T_INIT, T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__))
def cache(name, fn):
    p = os.path.join(HERE, 'data', name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p): return json.load(open(p))
    v = fn(); json.dump(v, open(p, 'w')); return v
