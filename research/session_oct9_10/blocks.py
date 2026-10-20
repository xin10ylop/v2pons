import json
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WAL = "ab5a34c3f4"
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)], key=lambda p: pools[p]["bn"])
for n, pid in enumerate(mine, 1):
    p = pools[pid]; ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    B = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY][0]
    pull = min(int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(B - 2, pull + 1)])
    print(f"\n== T{n} token {p['token'][:8]} deployer {p['deployer'][:8]} buy {B} pull +{pull-B}")
    for b in blks:
        bn = int(b["number"], 16)
        rows = []
        for t in b["transactions"]:
            if t["type"] == "0x6a": continue
            frm = t["from"][2:10]; to = (t.get("to") or "")[2:10]; inp = t["input"]
            tag = ""
            if p["token"] in inp.lower(): tag = "TOKEN"
            if t["from"][2:].lower() == p["deployer"]: tag += " DEPLOYER"
            if t["from"][2:12] == WAL: tag += " US"
            if tag or int(t["value"], 16) > 0 and to not in ("8876789976"[:8],):
                rows.append(f"{int(t['transactionIndex'],16)}:{frm}->{to} v{int(t['value'],16)/1e18:.5f} {inp[:10]} {tag}")
        print(f"  +{bn-B:2d} ntx {len(b['transactions'])}: " + " | ".join(rows))
