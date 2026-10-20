"""Token templates: eth_getCode of every token launched in the window (the non-ETH side; both sides of a non-ETH pair), stored as size, keccak,
and the PUSH4 set of the bytecode (a signature that survives immutables). Cached in s17_codes_cache.jsonl; then the template match per cluster:
the 2.4333 token's exact code hash, and its size + PUSH4 set."""
import json, collections, time
from clusters import load
from common import R, keccak, load_jsonl, append_jsonl
E = "0x" + "0" * 40
rows = load()
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
toks = sorted({c for r in rows for c in (r["c0"], r["c1"]) if c != E})
have = {x["a"] for x in load_jsonl("s17_codes_cache.jsonl")}
need = [t for t in toks if t not in have]
print("tokens", len(toks), "to fetch", len(need))
for i in range(0, len(need), 100):
    ch = need[i:i + 100]
    cs = R.batch("eth_getCode", [[t, "latest"] for t in ch], n=20)
    append_jsonl("s17_codes_cache.jsonl", [{"a": t, "size": (len(c) - 2) // 2, "hash": keccak(bytes.fromhex(c[2:])).hex(), "p4": sorted(push4(bytes.fromhex(c[2:])))} for t, c in zip(ch, cs) if c is not None])
    if i % 1000 == 0: print(i, R.STATS, flush=True)
code = {x["a"]: x for x in load_jsonl("s17_codes_cache.jsonl")}
tok = lambda r: r["c1"] if r["c0"] == E else r["c1"]
fam_code = collections.defaultdict(collections.Counter)
for r in rows:
    c = code.get(r["c1"])
    if c: fam_code[r["fam"].split(" (")[0]][(c["size"], c["hash"][:12])] += 1
for f in ("VB 2.4333", "VB 3.0", "VB 5.0"):
    print(f, "token code (size, hash) kinds:", len(fam_code[f]), fam_code[f].most_common(3))
ref = [code[r["c1"]] for r in rows if r["fam"].startswith("VB 2.4333") and r["c1"] in code]
H433 = {c["hash"] for c in ref}; P433 = {tuple(c["p4"]) for c in ref}; S433 = {c["size"] for c in ref}
ref3 = [code[r["c1"]] for r in rows if r["fam"].split(" (")[0] in ("VB 3.0", "VB 5.0") and r["c1"] in code]
P35 = collections.Counter(tuple(c["p4"]) for c in ref3).most_common(1)[0][0]
print("2.4333 token: sizes", S433, "distinct hashes", len(H433), "PUSH4 sets", len(P433), "| 3.0/5.0 token PUSH4 set size", len(P35))
for name, test in (("same code hash as a 2.4333 token", lambda c: c["hash"] in H433), ("same size + PUSH4 set as a 2.4333 token", lambda c: c["size"] in S433 and tuple(c["p4"]) in P433),
                   ("same PUSH4 set as the 3.0/5.0 token", lambda c: tuple(c["p4"]) == P35)):
    g = collections.defaultdict(list)
    for r in rows:
        for t in (r["c0"], r["c1"]):
            c = code.get(t)
            if c and test(c): g[r["fam"]].append(r); break
    print("\n== launches whose token has %s: %d in %d clusters" % (name, sum(len(v) for v in g.values()), len(g)))
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        print("   %4d  %-62s %s..%s" % (len(v), k[:62], time.strftime("%d %H:%M", time.gmtime(v[0]["t"])), time.strftime("%d %H:%M", time.gmtime(v[-1]["t"]))))
