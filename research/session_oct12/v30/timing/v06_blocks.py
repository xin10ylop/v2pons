"""Every tx in blocks L+12..T for a set of 3.0 pools: discovery = every 4th pool launched 05:37-11:59, held out = every pool launched 12:00 on.
Blocks are read hashes-only; the per-block 48 KB oracle push (index 1, to 0xd7572f7e) is identified from its receipt and not downloaded;
every other tx is read in full and stored compactly (from, to, selector, length, value, nonce, index, address words in the input)."""
import vc, json, os, re, collections
R = vc.R
P = json.load(open(vc.p("v03_pools.json"))); P.sort(key=lambda o: o["L"])
ORACLE = "0xd7572f7ed161d3c46ca86d7da52d94d4b2d104a9"
SPLIT = 1791806400  # Oct 12 12:00 UTC
disc = [o for o in P if o["t"] < SPLIT][::4]; held = [o for o in P if o["t"] >= SPLIT]
json.dump({"disc": [o["id"] for o in disc], "held": [o["id"] for o in held]}, open(vc.p("v06_sets.json"), "w"))
print("discovery", len(disc), "held out", len(held))
blocks = collections.defaultdict(set)
for o in disc + held:
    for b in range(o["L"] + 12, o["T"] + 1): blocks[vc.hh(o["t"])].add(b)
ADDR = re.compile(r"000000000000000000000000([0-9a-f]{40})")
def addrs(inp):
    s = inp[10:]; out = []
    for k in range(0, len(s) - 63, 64):
        m = ADDR.fullmatch(s[k:k + 64])
        if m and int(m.group(1), 16) > 0xffffffffff: out.append(m.group(1)[:16])
    return sorted(set(out))[:40]
for h in sorted(blocks):
    fn = vc.p("v06_blk_%s_cache.jsonl" % h); have = set()
    if os.path.exists(fn):
        for l in open(fn): have.add(json.loads(l)["b"])
    need = sorted(blocks[h] - have)
    print(h, "blocks", len(blocks[h]), "to fetch", len(need), flush=True)
    for i in range(0, len(need), 40):
        ch = need[i:i + 40]
        bl = R.batch("eth_getBlockByNumber", [[hex(b), False] for b in ch], n=20)
        idx1 = [b["transactions"][1] for b in bl if len(b["transactions"]) > 1]
        rc = dict(zip(idx1, R.batch("eth_getTransactionReceipt", [[x] for x in idx1], n=20)))
        want = [x for b in bl for k, x in enumerate(b["transactions"]) if not (k == 1 and rc[x] and (rc[x].get("to") or "").lower() == ORACLE)]
        tx = dict(zip(want, R.batch("eth_getTransactionByHash", [[x] for x in want], n=20)))
        with open(fn, "a") as f:
            for b in bl:
                rows = []
                for k, x in enumerate(b["transactions"]):
                    if x in tx and tx[x]:
                        t = tx[x]; inp = t["input"]
                        rows.append({"h": x, "f": t["from"].lower(), "to": (t.get("to") or "").lower(), "s": inp[:10], "cl": (len(inp) - 2) // 2, "v": int(t["value"], 16), "n": int(t["nonce"], 16), "i": k,
                                     "a": addrs(inp) if len(inp) < 20000 else []})
                    else:
                        r = rc.get(x) or {}
                        rows.append({"h": x, "f": (r.get("from") or "").lower(), "to": (r.get("to") or "").lower(), "s": "oracle", "cl": -1, "v": 0, "n": -1, "i": k, "a": []})
                f.write(json.dumps({"b": int(b["number"], 16), "t": int(b["timestamp"], 16), "txs": rows}) + "\n")
print("posts", R.STATS)
