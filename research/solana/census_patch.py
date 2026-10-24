#!/usr/bin/env python3
"""census_patch.py CENSUS.json OUT.json: fills the gaps a census.py run left (read-only; HELIUS_API_KEY).

census.py asks getTransaction for version-0 transactions only, so a creation or a creator's first transaction in Solana's newer version-1
format failed after 12 tries and was skipped (the run's 'failed' counts). Through census_fast.rpc (which asks again allowing version 1)
this re-lists the creation-fee accounts over the census's window, parses the creations missing from it, profiles every creator that has
no profile, and reads the pull for the new pools. Writes the merged census to OUT with 'patched' counts."""
import json, os, sys, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C
import census_fast as CF

C.rpc = CF.rpc


def main(src, out):
    d = json.load(open(src)); have = {p["sig"] for p in d["pools"]}; new = []
    for kind, (prog, fee) in C.PROG.items():
        sigs = [s["signature"] for s in C.sigs_since(fee, d["t0"]) if not s["err"] and s["signature"] not in have]
        print(f"{kind}: {len(sigs)} creations missing from the census", flush=True)
        with cf.ThreadPoolExecutor(6) as ex:
            new += [r for r in ex.map(lambda s: C.safe(C.parse, "parse")(kind, s), sigs) if r]
    d["pools"] += new
    sol = [p for p in d["pools"] if p.get("sol")]
    need = sorted({p["creator"] for p in sol if "n" not in p})
    print(f"{len(new)} creations recovered ({sum(1 for p in new if p.get('sol'))} with a SOL side); {len(need)} creators without a profile", flush=True)
    prof = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for cp in ex.map(C.safe(C.creator_profile, "creator"), need):
            if cp:
                prof[cp[0]] = cp[1]
    todo = [p for p in sol if "lp_later" not in p]
    with cf.ThreadPoolExecutor(6) as ex:
        pulls = {sp[0]: sp[1] for sp in ex.map(C.safe(C.pull_info, "pull"), todo) if sp}
    for p in sol:
        if p["creator"] in prof:
            p.update(prof[p["creator"]])
        if p["sig"] in pulls:
            p.update(pulls[p["sig"]])
    d["patched"] = {"creations": len(new), "creators": len(prof), "pulls": len(pulls), "still_failed": dict(C.FAILED)}
    json.dump(d, open(out, "w"))
    print(f"done -> {out}: {d['patched']} rpc {dict(CF.STATS)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
