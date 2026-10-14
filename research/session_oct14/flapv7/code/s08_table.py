"""s08: the exit-test table in detail (outsiders who bought before +100 vs the crowd vs the dev): hold length to the first move out,
whether the whole position left, exit method, buyer type (fingerprint), and example addresses / transactions. -> data/s08_table.json, stdout"""
import json, collections as C, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
S = json.load(open(os.path.join(D, "s05_holders.json"))); H6 = json.load(open(os.path.join(D, "s06_head.json")))
head = {(r["token"], r["holder"]): r for r in H6["rows"]}
P = "0xe2ce6ab8"
def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1); return round(xs[f] + (xs[c] - xs[f]) * (k - f), 1)
def typ(o):
    f = o["buys"][0]["fp"]
    if f.startswith(P): return "Portal-direct EOA"
    return "router/bot " + f.split(":")[0]
out = {}
for grp, sel in (("outsider<+100", lambda o: o["cls"] == ["outsider"] and o["first_off"] < 100),
                 ("outsider>=+100", lambda o: o["cls"] == ["outsider"] and o["first_off"] >= 100),
                 ("crowd", lambda o: "crowd" in o["cls"]), ("dev", lambda o: "dev" in o["cls"])):
    g = [o for o in S["rows"] if sel(o) and o["can_hold"]]
    held = [o for o in g if o["first_out"] is not None and o["first_out"] >= 200]
    early = [o for o in g if o["first_out"] is not None and o["first_out"] < 200]
    still = [o for o in g if o["first_out"] is None]
    hb = head
    rest = [o for o in g if (o["token"], o["holder"]) in hb and hb[(o["token"], o["holder"])].get("bal", 0) > 0]
    print(f"\n### {grp}: {len(g)} pairs, {len(set(o['holder'] for o in g))} holders, {len(set(o['token'] for o in g))} launches")
    print(f"  held >= 200 blocks, then moved out OK : {len(held)}  (hold to first exit p10/50/90 {[pct([o['first_out'] for o in held], q) for q in (.1,.5,.9)]})")
    print(f"  moved out before 200 blocks            : {len(early)}  (p50 {pct([o['first_out'] for o in early], .5)})")
    print(f"  never moved out (still holding)        : {len(still)}")
    print(f"  with a balance at the head             : {len(rest)}; transfer(dEaD,1%) ok {sum(1 for o in rest if hb[(o['token'],o['holder'])].get('transfer_dead')=='ok')}, Portal sell ok {sum(1 for o in rest if hb[(o['token'],o['holder'])].get('portal_sell')=='ok')} (3 dust at 1% = AmountTooSmall, full-balance sell ok)")
    print(f"  exit method of first move: Portal sell {sum(1 for o in held+early if o['outs'][0]['sold_portal'])}, plain transfer {sum(1 for o in held+early if not o['outs'][0]['sold_portal'])}")
    full = [o for o in held + early if o["bal_logs"] == 0]
    print(f"  fully exited {len(full)} of {len(held)+len(early)} that moved")
    print("  buyer type:", C.Counter(typ(o) for o in g).most_common(6))
    print("  held>=200 by type:", C.Counter(typ(o) for o in held).most_common(6))
    print("  bought-at offsets p10/50/90:", [pct([o['first_off'] for o in g], q) for q in (.1, .5, .9)])
    ex = sorted(held, key=lambda o: -o["first_out"])[:6]
    for o in ex:
        b = o["buys"][0]; x = o["outs"][0]
        print(f"   e.g. holder {o['holder']} token {o['token']} buy +{b['off']} tx {b['h']} ({b['eth']/1e18:.4f} BNB, {b['fp']}) -> first exit {x['after_buy']} blocks later tx {x['h']} sold_portal={x['sold_portal']}")
    out[grp] = {"pairs": len(g), "held200_ok": len(held), "early": len(early), "still": len(still), "with_bal_head": len(rest),
                "hold_p50": pct([o['first_out'] for o in held], .5), "examples": [(o["holder"], o["token"], o["buys"][0]["h"], o["outs"][0]["h"], o["first_out"]) for o in ex]}
json.dump(out, open(os.path.join(D, "s08_table.json"), "w"), indent=1)
