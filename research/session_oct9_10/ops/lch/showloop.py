import json, sys
f = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
rows = [json.loads(l) for l in open(f)]
print(len(rows), "steps")
odd = 0
for r in rows[-k:]:
    if "stop" in r: print("STOP", r); continue
    flag = ""
    fams_in = set(r["in_fams"]) - {"-"}; fams_out = set(r["out_fams"]) - {"-"}
    if len(fams_in | fams_out) > 1: flag += " MIXED"
    if r["odd_in"] and len(r["odd_in"]) > 1: flag += " MULTI-ODD-IN"
    print(r["step"], r["utc"], r["addr"][:10], "n0", r["nonce0"], "cap", r["cap_eth"], "->", r["cap_to"][:10], r["cap_to_lab"], "| out", r["n_plain_out"], r["out_fams"], "| in", r["n_in"], r["in_fams"], r["in_eth"], "|", [(c[0][:10], c[1]) for c in r["calls"]][:4], flag)
