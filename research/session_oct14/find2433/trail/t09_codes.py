"""Token templates since the stop: eth_getCode of every token in every Initialize since block 86314100 (t04), stored as size, keccak and
the PUSH4 set (t09_codes_cache.jsonl). Matches against the 2.433 token (1,526 B, one code hash; Oct 12 fp/s17 cache) and the 3.0/5.0
token's PUSH4 set; also the code hash of every recurring 1B-token mint recipient (t08_bigmints) against the bot router's code hash."""
from common import *
import collections
E = ZERO
def push4(b):
    out = set(); i = 0
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            if n == 4: out.add(b[i + 1:i + 5].hex())
            i += n + 1
        else: i += 1
    return out
inits = jl(J("t04_inits_cache.jsonl"))
toks = sorted({c for r in inits for c in (r["c0"], r["c1"]) if c != E})
old = {x["a"]: x for x in jl("/home/user/v2pons/research/session_oct12/v2433/fp/s17_codes_cache.jsonl")}
have = {x["a"]: x for x in jl(J("t09_codes_cache.jsonl"))}
mints = jl(J("t08_bigmints_cache.jsonl"))
rc = collections.Counter(r["to"] for r in mints)
recips = [a for a, n in rc.items() if n >= 3]
need = [t for t in toks + recips if t not in have]
print("tokens", len(toks), "mint recipients", len(recips), "to fetch", len(need), flush=True)
with open(J("t09_codes_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        ch = need[i:i + 100]
        cs = rpc.batch("eth_getCode", [[t, "latest"] for t in ch], n=20)
        for t, c in zip(ch, cs):
            if c is None: continue
            b = bytes.fromhex(c[2:]); r = {"a": t, "size": len(b), "hash": keccak(b).hex(), "p4": sorted(push4(b))}
            have[t] = r; f.write(json.dumps(r) + "\n")
        if i % 1000 == 0: print(i, rpc.STATS, flush=True)
# references
ref433 = [x for x in old.values() if x["size"] == 1526]
H433 = collections.Counter(x["hash"] for x in ref433); print("2.433 reference hashes (Oct 12 cache, size 1526):", H433.most_common(3))
P433 = {tuple(x["p4"]) for x in ref433 if x["hash"].startswith("63ad5291cdef")}
P35 = collections.Counter(tuple(x["p4"]) for x in old.values() if x["size"] == 5274).most_common(1)[0][0]
print("router hash", BOT_CODE_HASH[:12])
for a in recips:
    c = have.get(a)
    print("  mint recipient", a, "mints", rc[a], "code", c and c["size"], c and c["hash"][:12], "ROUTER CLONE" if c and c["hash"] == BOT_CODE_HASH else "")
hit = collections.Counter(); p35 = collections.Counter(); s1526 = collections.Counter()
ltx = {}
for r in inits:
    for t in (r["c0"], r["c1"]):
        c = have.get(t)
        if not c: continue
        key = (r["c0"] == E, r["fee"], r["ts"])
        if c["hash"].startswith("63ad5291cdef"): hit[key] += 1; print("2.433 TOKEN CODE", r)
        if c["size"] == 1526 or (c["size"] and tuple(c["p4"]) in P433): s1526[(key, c["size"], c["hash"][:12])] += 1
        if tuple(c["p4"]) == P35: p35[key] += 1
print("launches with the exact 2.433 token code since the stop:", sum(hit.values()), dict(hit))
print("launches with a 1,526-B token or the 2.433 PUSH4 set:", s1526.most_common(10))
print("launches whose token has the 3.0/5.0 PUSH4 set, by (ETH pair, fee, ts):", p35.most_common(20))
print(rpc.STATS)
