import json, gzip, collections
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
def load(files=("/home/user/v2pons/research/data/slowrug_op.json.gz",)):
    P, S, L, T, TS = {}, {}, {}, {}, {}
    for f in files:
        d = json.load(gzip.open(f))
        P.update(d["pools"]); S.update(d["swaps"]); L.update(d["liquidity"]); T.update(d["txs"]); TS.update({int(k): v for k, v in d.get("launch_ts", {}).items()})
    return P, S, L, T, TS
