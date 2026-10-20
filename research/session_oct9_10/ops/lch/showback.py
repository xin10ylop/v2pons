import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
k = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
print(len(rows), "steps")
for r in rows[-k:]:
    if "stop" in r: print("STOP", r); continue
    fams = set(r["in_fams"]) - {"-"}
    flag = " MIXED" if len({f for f in fams if not f.startswith("DEP")}) > 1 else ""
    print(r["step"], r["utc"], r["addr"][:10], "<-", r["from"][:10], r["from_lab"], "n", r["from_nonce"], r["eth"], "| in", r["n_in"], r["in_fams"], r["in_eth"], flag, r["odd_in"][:2] if len(r["odd_in"]) > 1 else "")
