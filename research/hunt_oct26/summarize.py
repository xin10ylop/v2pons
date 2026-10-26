#!/usr/bin/env python3
"""summarize.py CHAIN [OUT.json]: everyone who made money at the front of pump-and-pull pools on CHAIN, over every roundtrips.py day in out/.

The early round trips (entry within 20 s of the liquidity add, profit = sell minus buy, the pool pulled within 2 h) are grouped by the
contract the buyer called:
  - a private contract (a bot's own router or relay): one group per contract, all its wallets together;
  - a public router (the Universal Router, a V2 router): one group per wallet.
A group that profits on pools of two or more operators (venue + tick spacing + hook) is an independent bot; a group whose wallets
each appear in one or two pools of a single line, with one stake, is that line's own fleet recycling its money (e.g. the tick-spacing-1
line's 0x5a1d33c4...777 router: 13 wallets x 0.35 ETH on Sep 19). Prints the groups by profit with their active days, the lines they hit and
when, and then the lines ranked by what independent groups took out of them, day by day. Read-only (reads out/ only)."""
import sys, os, json, glob, collections, statistics as st

PUBLIC = {"rh": {"0x8876789976decbfcbbbe364623c63652db8c0904", "0x89e5db8b5aa49aa85ac63f691524311aeb649eba"},
          "base": {"0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x6ff5693b99212da76ad316178a184ab56d299b43", "0x8cfe327cec66d1c090dd72bd0ff11d690c33a2eb",
                   "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x2626664c2603336e57b271c5c0b26f421741e481"}}
OURS = {"0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8": "us (Robinhood engine)", "0x492a40b43ce221ec2c952cda473f441e365dea62": "us (Base engine)",
        "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc": "D65 crew router", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758": "D65 crew router (twin)"}


STABLE = set()                                             # launch contracts seen in 3+ pools; the rest are per-pool launcher copies
def shape(f):
    """an operator's key: venue, tick spacing and hook. Fee tier, size and launch contract apart: operator A alone uses fees 0.05-6%, its
    fixed launcher and a fresh launcher copy per pool. Operator A and the volume bot share a key (tick spacing 200), which only makes the
    test stricter; the 2.433 line (50/100), the tick-spacing-1 line, the V2 lines and the hooked launchpads stay apart."""
    w = f[0].split()
    return (w[0], w[4], "hook" in w)


REAL = 0.001


def fam_name(f):
    return f"{f[0]} x {f[1]:g} via {(f[2] if f[2] in STABLE else 'per-pool launchers' if f[2] else '-')[:18]}"


def main(ch, out=None):
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, f"out/rt_{ch}_2*.json")))
    G = collections.defaultdict(list)
    days = []
    for f in files:
        d = json.load(open(f)); day = os.path.basename(f)[len(f"rt_{ch}_"):-5]; days.append(day)
        for t in d["early"]:
            if not t.get("who") or t["who"] == t.get("launcher"):
                continue
            t["day"] = day
            key = ("wallet", t["who"]) if (t.get("via") in PUBLIC.get(ch, ()) or not t.get("via")) else ("contract", t["via"])
            G[key].append(t)
    tp = collections.defaultdict(set)
    for ts in G.values():
        for t in ts:
            tp[t["fam"][2]].add(t["pool"])
    STABLE.update(a for a, ps in tp.items() if a and len(ps) >= 3)
    rows = []
    for key, ts in G.items():
        pnl = sum(t["pnl"] for t in ts)
        wallets = collections.Counter(t["who"] for t in ts)
        pools = {t["pool"] for t in ts}
        targets = collections.Counter(shape(t["fam"]) for t in ts)
        shapes = collections.Counter(fam_name(t["fam"]) for t in ts)
        dd = sorted({t["day"] for t in ts})
        rows.append({"kind": key[0], "id": key[1], "pnl": pnl, "trips": len(ts), "wins": sum(t["pnl"] > 0 for t in ts), "pools": len(pools),
                     "wallets": len(wallets), "pools_per_wallet": round(len(pools) / len(wallets), 1), "targets": len(targets),
                     "stake_med": st.median(t["paid"] for t in ts), "ret_med": st.median(t["pnl"] / t["paid"] for t in ts if t["paid"] > 0),
                     "in_med": st.median(t["in_s"] for t in ts), "out_med": st.median(t["out_s"] for t in ts), "first": dd[0], "last": dd[-1], "days": len(dd),
                     "lines": shapes.most_common(5), "top_wallets": wallets.most_common(3),
                     "ours": OURS.get(key[1]) or next((OURS[w] for w in wallets if w in OURS), "")})
    rows.sort(key=lambda r: -r["pnl"])
    print(f"{ch}: {len(files)} days ({days[0] if days else '-'} .. {days[-1] if days else '-'}), {sum(len(v) for v in G.values())} early outside round trips, {len(G)} groups")
    print(f"\n== independent groups (2+ operators, 3+ pools a wallet, or known) trading a real stake (median {REAL:g}+), and the rest that made 0.01+")
    for r in rows:
        r["indep"] = bool(r["ours"]) or (r["targets"] >= 2 and r["pools_per_wallet"] >= 3)
        if r["pools"] < 3 or not ((r["indep"] and r["stake_med"] >= REAL and r["pnl"] > 0) or r["pnl"] >= 0.01):
            continue
        indep = "INDEPENDENT" if r["indep"] else ("fleet-like" if r["pools_per_wallet"] < 2 else "one pool type")
        print(f"  {r['kind']:8s} {r['id']} {r['ours']}\n      pnl {r['pnl']:+.4f} won {r['wins']}/{r['trips']} pools {r['pools']} wallets {r['wallets']} ({r['pools_per_wallet']}/wallet)"
              f" targets {r['targets']} | stake {r['stake_med']:.5f} ret {r['ret_med']:+.0%} in {r['in_med']:.1f}s out {r['out_med']:.1f}s | {r['first']}..{r['last']} ({r['days']} d) | {indep}")
        for name, n in r["lines"][:4]:
            print(f"        {n:5d} x {name}")
    print(f"\n== single-operator groups at a real stake (median {REAL:g}+, 10+ pools, 3+ pools a wallet): a line's recurring fleet or a dedicated"
          " fronter; front.py's rug test on the line decides")
    for r in rows:
        if not r["indep"] and r["stake_med"] >= REAL and r["pools"] >= 10 and r["pools_per_wallet"] >= 3 and r["pnl"] > 0:
            print(f"  {r['kind']:8s} {r['id']} pnl {r['pnl']:+.4f} won {r['wins']}/{r['trips']} pools {r['pools']} wallets {r['wallets']} | stake {r['stake_med']:.4f}"
                  f" ret {r['ret_med']:+.0%} in {r['in_med']:.1f}s out {r['out_med']:.1f}s | {r['first']}..{r['last']} ({r['days']} d) | {r['lines'][0][0]} ({r['lines'][0][1]})")
    # lines by what the independent groups took, per day
    indep_keys = {(r["kind"], r["id"]) for r in rows if r.get("indep") and r["pnl"] > 0}
    L = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0.0, set(), []]))
    for key in indep_keys:
        for t in G[key]:
            if t["paid"] < REAL:                           # the owner's rule: a seat that only takes dust is not a seat
                continue
            x = L[fam_name(t["fam"])][t["day"]]; x[0] += 1; x[1] += t["pnl"] > 0; x[2] += t["pnl"]; x[3].add(key[1]); x[4].append(t["paid"])
    print(f"\n== lines by what independent groups took out at a real stake ({REAL:g}+; per day: trips, won, pnl, groups, median stake)")
    ranked = sorted(L.items(), key=lambda kv: -sum(v[2] for v in kv[1].values()))
    for name, per in ranked[:25]:
        tot = sum(v[2] for v in per.values())
        if tot < 0.005:
            break
        print(f"  {name}: total {tot:+.4f} over {len(per)} days")
        for day in sorted(per):
            v = per[day]
            print(f"      {day} {', '.join(sorted(g[:10] for g in v[3]))} trips {v[0]:4d} won {v[1]:4d} pnl {v[2]:+.5f} groups {len(v[3])} stake {st.median(v[4]):.5f}")
    here_out = os.path.join(here, f"out/indep_{ch}.json")
    json.dump(sorted(r["id"] for r in rows if r.get("indep") and r["pnl"] > 0), open(here_out, "w"))     # routers and wallets
    if out:
        json.dump({"chain": ch, "days": days, "groups": rows}, open(out, "w"), default=list)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
