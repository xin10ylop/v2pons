"""read every no-arg view of a curve at given blocks (archive eth_call test)."""
import json, sys
from krpc import *
S = json.load(open(os.path.join(OUT, "k04_selectors.json")))["curve_bf44"]["selectors"]
curve = sys.argv[1]; blocks = sys.argv[2:]
for b in blocks:
    bb = b if b == "latest" else hex(int(b))
    r = post([{"jsonrpc": "2.0", "id": i, "method": "eth_call", "params": [{"to": curve, "data": "0x" + s}, bb]} for i, s in enumerate(S)])
    got = {x["id"]: x for x in r}; row = {}
    for i, s in enumerate(S):
        x = got.get(i, {})
        if "result" in x and len(x["result"]) > 2:
            d = x["result"]; ws = [int(d[2 + 64 * j:2 + 64 * (j + 1)], 16) for j in range((len(d) - 2) // 64)]
            row[s] = [hex(w) if 2**140 < w < 2**160 else w for w in ws]
        elif "error" in x: row[s] = "ERR " + str(x["error"].get("message"))[:60]
    print(b, json.dumps(row))
