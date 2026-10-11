"""eth_call every dispatcher selector with no arguments (views answer; others revert). Read-only simulation."""
import json
from krpc import *
S = json.load(open(os.path.join(OUT, "k04_selectors.json")))
C = json.load(open(os.path.join(DATA, "codes.json")))
res = {}
for k in ("curve_bf44", "factory", "router_e33e", "feeto_31ea", "token_d564", "router_9dcc"):
    a = C[k]["addr"]; sels = list(S[k]["selectors"])
    r = post([{"jsonrpc": "2.0", "id": i, "method": "eth_call", "params": [{"to": a, "data": "0x" + s}, "latest"]} for i, s in enumerate(sels)])
    got = {x["id"]: x for x in r}
    res[k] = {}
    print(k, a)
    for i, s in enumerate(sels):
        x = got.get(i, {})
        if "result" in x and len(x["result"]) > 2:
            d = x["result"]; words = [d[2 + 64 * j:2 + 64 * (j + 1)] for j in range((len(d) - 2) // 64)]
            res[k][s] = d
            print("   ", s, S[k]["selectors"][s], [("0x" + w[24:]) if w[:24] == "0" * 24 and int(w, 16) > 2**100 else int(w, 16) for w in words[:8]])
json.dump(res, open(os.path.join(OUT, "k05_views.json"), "w"), indent=1)
