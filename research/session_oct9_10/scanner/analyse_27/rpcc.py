"""cached RPC helper for analyse_27: every answer kept in cache/rpc.jsonl keyed by (method, params)"""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
import chain
HERE = os.path.dirname(os.path.abspath(__file__)); CF = os.path.join(HERE, "cache", "rpc.jsonl")
_C = {}
if os.path.exists(CF):
    for line in open(CF):
        try: k, v = json.loads(line); _C[k] = v
        except Exception: pass
def _k(m, p): return json.dumps([m, p], sort_keys=True)
def call_many(calls):
    need = [(m, p) for m, p in calls if _k(m, p) not in _C]
    if need:
        res = chain.batch(need)
        with open(CF, "a") as f:
            for (m, p), r in zip(need, res):
                if r is None: continue
                _C[_k(m, p)] = r; f.write(json.dumps([_k(m, p), r]) + "\n")
    return [_C.get(_k(m, p)) for m, p in calls]
def call(m, p): return call_many([(m, p)])[0]
