"""Tally v4 Initialize events in a creations file by hooks address and label via Uniswap hooklist.json."""
import json, sys, collections, os
here = os.path.dirname(__file__)
hl = json.load(open(os.path.join(here, "..", "dl", "hooklist.json")))
names = {}
for h in hl:
    hk = h["hook"]; names[(hk["chainId"], hk["address"].lower())] = hk.get("name")
fn, chain_id = sys.argv[1], int(sys.argv[2])
INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"
c = collections.Counter(); pairs = collections.Counter()
for line in open(fn):
    l = json.loads(line)
    if l["topics"][0] != INIT: continue
    hooks = "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3]
    c[hooks.lower()] += 1
tot = sum(c.values())
print("total v4 Initialize", tot)
for h, n in c.most_common(15):
    print(n, round(100 * n / tot, 1), h, names.get((chain_id, h), "-"))
