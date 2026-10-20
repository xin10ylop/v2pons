"""Stream pools.jsonl once; keep the PositionManager multicall pools of the C-1 shape (and the census known_fp C-1 pools) -> c1_rows.jsonl.
C-1 core (ETH): dex v4, launch.to POSM, selector ac9650d8, calldata 2276, value 0, quote ETH, fee 100, tick spacing 1, hooks 0, tok skel cb79985d..."""
from common import *
keep = []; cnt = C.Counter(); skel = C.Counter(); fpc = C.Counter()
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if '"C-1"' not in line and '"calldata_len": 2276' not in line: continue
        r = json.loads(line)
        L = r["launch"]
        shape = (r["dex"] == "v4" and L["to"] == POSM and L["selector"] == "ac9650d8" and L["calldata_len"] == 2276 and L["value_wei"] == 0
                 and r["fee"] == 100 and r["tick_spacing"] == 1 and r["hooks"] == ZERO)
        if r["known_fp"] == "C-1" or shape:
            keep.append(r)
            cnt[(r["known_fp"], shape, r["quote"], (r["fam"]["tok"] or "")[:8])] += 1
with open(os.path.join(V, "c1_rows.jsonl"), "w") as g:
    for r in keep: g.write(json.dumps(r) + "\n")
for k, v in cnt.most_common(): print(v, k)
