#!/usr/bin/env python3
"""bytecode.py CHAIN OUT.json CENSUS.json...: the 2.433 operator, or its developer, under other wallets, found by token code instead of addresses.

For every pulled pool of the census files launched with 0.5+ native (the operator's sizes are 1.5-12; dust pools skipped), the token's
runtime code is read and compared with:
  exact    the 2.433 token (1,526 B, code hash 63ad5291cdef..., byte-identical on Robinhood, BNB and Base, address ending in 777);
           the reference is read from a real 2.433 token in the Oct 10 Robinhood census
  family   any code containing PUSH4 0x3c130d90: the unknown selector the 2.433 token shares with operator A's 1,770-byte tokens
           (research/session_oct9_10/STUDY_OCT10.md line 523), the same developer's template
Prints the matches per day, pool shape and launch size. Read-only, public RPCs."""
import sys, json, collections
import hlib as H

SEL = "633c130d90"


def ref_code():
    """the code of a real 2.433 token: one from the Oct 10 Robinhood census (v4, fee 2500, tick spacing 50, 2.4333 ETH)"""
    try:
        d = json.load(open("out/rh_1010_12.json"))["chains"]["rh"]
        tok = next(p["tok"] for p in d["rugs"] if p["venue"] == "v4" and p.get("fee") == 2500 and abs((p.get("nat_in") or 0) - 2.4333) < 0.001)
        return H.rpc(H.CH["rh"]["rpc"], "eth_getCode", [tok, "latest"])
    except (OSError, StopIteration):
        return None


def main(ch, out, files):
    ref = ref_code()
    print(f"reference 2.433 token code: {len(ref) // 2 - 1 if ref else '?'} B", flush=True)
    url = H.CH[ch]["rpc"]; rows = []
    for f in files:
        d = json.load(open(f))["chains"][ch]; day = f.split(f"{ch}_")[-1][:11]
        ps = [p for p in d["rugs"] if (p.get("nat_in") or 0) >= 0.5]
        codes = H.batch(url, [("eth_getCode", [p["tok"], "latest"]) for p in ps], size=20, workers=3)
        g = collections.Counter()
        for p, c in zip(ps, codes):
            if not c:
                continue
            ex = ref is not None and c == ref; fam = SEL in c
            if ex or fam:
                shape = f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", H.ZERO) != H.ZERO else "")
                g[(shape, round(p["nat_in"], 4), "exact" if ex else f"family {len(c) // 2 - 1} B", p.get("to"))] += 1
                rows.append({"day": day, "pool": p["id"], "tok": p["tok"], "shape": shape, "nat_in": p["nat_in"], "exact": ex, "size": len(c) // 2 - 1,
                             "to": p.get("to"), "frm": p.get("frm")})
        print(f"{ch} {day}: {len(ps)} pulled pools of 0.5+ read, {sum(g.values())} matches", flush=True)
        for k, v in g.most_common(8):
            print(f"    {v:4d} {k[0]:26s} x {k[1]:<9g} {k[2]:18s} via {k[3]}", flush=True)
    json.dump(rows, open(out, "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
