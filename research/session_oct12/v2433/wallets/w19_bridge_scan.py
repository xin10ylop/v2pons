"""Every Across-style FundsDeposited (topic 0x32ed1a40) on the Robinhood Chain spoke pool 0xd29c85f1 from Oct 10 00:00 UTC to the head:
depositor, recipient, amounts, destination chain; then the deposits by the known wallets and the deposits to the same recipient."""
from common import *
import collections
SP = "0xd29c85f15df544ba632c9e25829fd29d767d7978"
OUT = J("w19_dep_cache.jsonl")
done = jl(OUT); last = max([d["b"] for d in done], default=None)
h, th = head()
start = 84500000 if last is None else last + 1
with open(OUT, "a") as f:
    for a in range(start, h + 1, 100000):
        for l in rpc.logs({"address": SP, "topics": ["0x32ed1a409ef04c7b0227189c3a103dc5ac10e775a15b785dcc510201f7c25ad3"]}, a, min(a + 99999, h)):
            d = l["data"][2:]; w = [d[i:i + 64] for i in range(0, len(d), 64)]
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "dest": int(l["topics"][1], 16), "depositor": "0x" + l["topics"][3][-40:],
                                "in_tok": "0x" + w[0][-40:], "in": int(w[2], 16), "out": int(w[3], 16), "recipient": "0x" + w[7][-40:]}) + "\n")
        print("scanned", a, flush=True)
rows = jl(OUT)
print("deposits", len(rows), "blocks", min(r["b"] for r in rows), "..", max(r["b"] for r in rows))
R = "0x4216e5ae6021c523aae05b6ac6824f3c096cf905"; HUB = "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"
known = {HUB: "2.433 hub", "0x544ef4354283261fb9e258247a80d49c86b9f107": "decoy collector 544ef435", "0xe322fc6ddb6b29d110b7f84c728d2d743e904616": "decoy collector e322fc6d",
         "0x488faf521a2d5f16ee55d1335841bb3ba9a0946e": "decoy funder 488faf52", "0x8cf143ddc84dedcd7bedd2b362b63af154dfa4f7": "fronter 8cf143dd", "0xb8c879dcd96d5ce0719e6fb056738f09b33bc33c": "fronter b8c879dc",
         "0x0c628d6535b781f6c703ad319af8b1bcec63fbb4": "decoy-router admin", "0x04a802fe42476e9e9ed3cc3c28ce3a476a73d229": "fd1b271f admin", "0x39525d91ffdcc126f052eefed6735fda72ad1dee": "0x39525d91 (0.7999 sender)"}
try:
    ch = json.load(open(J("w06_chain.json"))); 
    for x in ch["launches"]: known.setdefault(x["w"], "2.433 launch wallet")
    for e in ch["events"]:
        if e["nonce"] > 30000: known.setdefault(e["f"], "2.433 buyer")
except Exception: pass
print("to recipient", R, ":", [(r["b"], r["depositor"], r["in"] / 1e18, r["dest"]) for r in rows if r["recipient"] == R])
print("by known wallets:", [(r["b"], known[r["depositor"]], r["in"] / 1e18, r["recipient"], r["dest"]) for r in rows if r["depositor"] in known])
print("recipients that are known wallets:", [(r["b"], r["depositor"], known[r["recipient"]], r["in"] / 1e18) for r in rows if r["recipient"] in known])
big = sorted(rows, key=lambda r: -r["in"])[:12]
print("largest deposits:", [(r["b"], r["depositor"][:10], round(r["in"] / 1e18, 3), r["recipient"][:10], r["dest"]) for r in big])
print("deposits per destination:", collections.Counter(r["dest"] for r in rows).most_common(8))
print(rpc.STATS)
