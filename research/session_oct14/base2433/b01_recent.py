"""Base: the 2.433 operator's 31 buyer wallets were funded there (watch 09:53 UTC Oct 14: 21 hold 0.04-0.37 ETH, nonce sum +70 since 09:09).
Scan the last N Base blocks (full transactions, public endpoint, read-only) for transactions from or to those wallets and the operator's
keys, and print each one (block, time, from, to, selector, calldata length, value). usage: python3 b01_recent.py [blocks, default 400]"""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
buyers = {a.lower() for a, n, b in json.load(open(SRC + "c16_rh_wallets_xchain.json"))["buyers_bsc"]}
keys = {"0x0152c954397718abfe4716eb3aaf86903cff3796": "admin_0152", "0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d": "admin_5b2b",
        "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d": "hub_6c3b", "0x8b499c5a56d5d0bed60527463bb1de389d6327e1": "next_8b49",
        "0x31c8cf1c5edf64777d70727a92a6f46b6b794664": "consol_31c8"}
watch = buyers | set(keys)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16)
hits = []; tos = collections.Counter()
for a in range(head - N + 1, head + 1, 10):
    bl = xr.batch("base", "eth_getBlockByNumber", [[hex(b), True] for b in range(a, min(a + 10, head + 1))], n=10)
    for B in bl:
        if not B: continue
        for t in B["transactions"]:
            f = t["from"].lower(); to = (t.get("to") or "").lower()
            if f in watch or to in watch:
                hits.append((int(B["number"], 16), int(B["timestamp"], 16), f, to, t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16) / 1e18, t["hash"]))
                tos[(to, t["input"][:10])] += 1
print(f"base head {head}: {len(hits)} transactions from/to the operator's wallets in the last {N} blocks")
for h in hits:
    lab = lambda x: keys.get(x, "buyer" if x in buyers else x[:10])
    print("  %d %s %s -> %s %s %d B %.6f %s" % (h[0], time.strftime("%H:%M:%S", time.gmtime(h[1])), lab(h[2]), lab(h[3]), h[4], h[5], h[6], h[7][:12]))
print("by (to, selector):", tos.most_common(10))
