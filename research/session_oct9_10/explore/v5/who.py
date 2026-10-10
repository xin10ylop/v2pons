import pickle, collections, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = pickle.load(open("cache.pkl","rb"))
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
wallet_pools = collections.defaultdict(set); role = collections.Counter(); to_c = collections.Counter(); fund = collections.Counter()
per = []
for pid, d in D.items():
    m = d["meta"]; b0 = m["b0"]
    tx = {}
    for b in d["blocks"]:
        for t in b["transactions"]: tx[t["hash"]] = t
    sw = []
    for l in sorted(d["logs"], key=lambda l:(int(l["blockNumber"],16), int(l["logIndex"],16))):
        bn = int(l["blockNumber"],16)
        if bn - b0 > 80: break
        t = tx.get(l["transactionHash"])
        if l["topics"][0] == T_SWAP:
            a0 = sgn(W(l["data"],0)); a0 = a0 - (1<<128) if a0 >= (1<<127) else a0
            frm = t["from"].lower() if t else "?"; to = (t["to"] or "").lower() if t else "?"
            sw.append((bn-b0, "buy" if a0 < 0 else "sell", abs(a0)/1e18, frm[:10], to[:10], (t["input"][:10] if t else "?"), int(t["value"],16)/1e18 if t else None))
            wallet_pools[frm].add(pid); role[(frm[:10], to[:10])] += 1
    per.append((m["src"], pid[:10], m["from"][:10], sw))
rec = {w for w, s in wallet_pools.items() if len(s) >= 2}
print("distinct swap wallets", len(wallet_pools), "in >=2 pools:", len(rec))
for w in sorted(wallet_pools, key=lambda w: -len(wallet_pools[w]))[:15]: print("  ", w, len(wallet_pools[w]))
print("(from, to) counts:", role.most_common(20))
for src, pid, dep, sw in per[:6]:
    print(src, pid, "deployer", dep)
    for s in sw[:25]: print("    ", s)
