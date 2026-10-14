"""Step 9c: code size + keccak of the token of every launch after the stop that is not VB 3.0/5.0, S1 or S2 (resumable; s09c_codes_cache.jsonl).
Looks for the 2.433 token template (1,526 B, keccak 63ad5291cdef...) and for any template shared by many launches."""
import collections
from common import *
rows = jload("s04_launches.json")
SKIP = {"VB 3.0", "VB 5.0", "S1 coin factory hook 0x4e346895", "S2 lift.fun 7866fa39"}
toks = sorted({r["tok"] for r in rows if r["b"] > 86310320 and r["fam"] not in SKIP})
have = {r["a"] for r in jl_load("s09c_codes_cache.jsonl")}
todo = [a for a in toks if a not in have]
print("tokens", len(toks), "todo", len(todo), flush=True)
for i in range(0, len(todo), 100):
    ch = todo[i:i + 100]
    cs = rpc.batch("eth_getCode", [[a, "latest"] for a in ch], n=10)
    out = []
    for a, c in zip(ch, cs):
        b = bytes.fromhex(c[2:]) if c and c != "0x" else b""
        out.append(dict(a=a, n=len(b), k=("0x" + keccak(b).hex()) if b else ""))
    jl_append(out, "s09c_codes_cache.jsonl")
    print(i + len(ch), rpc.STATS, flush=True)
C = {r["a"]: r for r in jl_load("s09c_codes_cache.jsonl")}
print("\n1,526-byte tokens:", [(a, C[a]["k"][:14]) for a in toks if C.get(a, {}).get("n") == 1526])
print("2.433 hash tokens:", [a for a in toks if C.get(a, {}).get("k", "").startswith("0x63ad5291cdef")])
kc = collections.Counter((C[a]["n"], C[a]["k"][:14]) for a in toks if a in C)
print("\nmost common token templates (size, hash) among", len(toks), "tokens:")
fam_of = collections.defaultdict(collections.Counter)
for r in rows:
    if r["tok"] in C and r["b"] > 86310320 and r["fam"] not in SKIP: fam_of[(C[r["tok"]]["n"], C[r["tok"]]["k"][:14])][r["fam"] or r["key"]] += 1
for k, v in kc.most_common(25): print("  %5d size %6d hash %s  in %s" % (v, k[0], k[1], fam_of[k].most_common(3)))
sz = collections.Counter(C[a]["n"] for a in toks if a in C)
print("\nsizes within 1,400-1,700 B:", sorted((s, n) for s, n in sz.items() if 1400 <= s <= 1700))
