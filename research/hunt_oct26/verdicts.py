#!/usr/bin/env python3
"""verdicts.py CHAIN: every line front.py tested, every day, in one table: its verdict (TRAP / TOLERANT / OPEN / CLOSED / UNTESTED), the paper
seat after the fleet's 1st and 3rd buy, and what happened to real-size outside buys (sold, rugged, held). Lines that match a line already
documented in the earlier reports are labelled with it (KNOWN below); the rest are printed first: a new line, by anyone.

A candidate seat is a line that is TOLERANT (real outside buys sold, at most a fifth rugged) or UNTESTED with a paper seat of +5% or more after
the fleet's first buy (what the 2.433 line looked like before anyone traded it). A TRAP (outside buys pulled on before the buyer could sell)
is skipped, whatever its paper seat. Read-only (reads out/ only)."""
import sys, os, glob, json, re, collections, statistics as st


# lines already documented (research/chase/REPORT_OCT20.md, REPORT_OCT21.md, REPORT_OCT23*.md, docs/HANDOFF.md): (regex on the line name, label)
KNOWN = {"rh": [(r"^v4 fee 2500 ts 50 x 2\.43|^v4 fee 5000 ts 100 x 2\.4", "the 2.433 line (the one that paid)"),
                (r"^v4 fee 10000 ts 200 x (3|5)$", "volume bot 3.0/5.0 (pull 5-21 blocks after any outside swap)"),
                (r"^v4 fee \d+ ts 200 ", "operator A family (whitelist + 0.0002 ETH counter)", "opA"),
                (r"^v4 fee 500 ts 1 ", "tick-spacing-1 wash line"),
                (r"^v4 fee 100 ts 1 ", "PM2276 fee-100 family"),
                (r"^v4 fee 2500 ts 25 hook", "bonding-curve graduation launchpad"),
                (r"^v2 fee - ts - ", "third operator's V2 tiers (factory 0x8bceaa40, router 0x89e5db8b; react to foreign buys)", "op3"),
                (r"^v4 fee (200000|8[0-9]{5}|9[0-9]{5}) ", "fee trap")],
         "base": [(r"^v4 fee 5000 ts 100 hook", "the 2.433 operator's Base line (base-0.2 traded it)"),
                  (r"^v4 fee 0 ts 1 x 1\.2", "1.2 ETH fee-0 tick-1 sniper trap / volume bot"),
                  (r"^v4 fee 100 ts 1 x 0\.501", "0.5013 ETH timer line (pulls 2-3 blocks after any outside buy)"),
                  (r"^v2 fee - ts - ", "Base V2 crew tiers (live-tested Oct 21: closed)")]}


def label(ch, name, targets=None):
    """targets: the launch transactions' targets of the line's pools. Operator A is a tick-200 line launched through its launcher 0x3194e326 or
    through a fresh launcher copy per pool; the third operator is a V2 line launched through its router 0x89e5db8b; launched any other way,
    the line is new"""
    for rx, lab, *cond in KNOWN.get(ch, []):
        if re.search(rx, name):
            if cond and cond[0] == "op3" and targets is not None:
                if collections.Counter(targets).most_common(1)[0][0] != "0x89e5db8b5aa49aa85ac63f691524311aeb649eba":
                    continue
            if cond and cond[0] == "opA" and targets is not None:
                c = collections.Counter(targets)
                fresh = sum(1 for v in c.values() if v == 1) >= 0.5 * len(targets)
                if not (c.most_common(1)[0][0] == "0x3194e32622c5d860a0572c74edda99dcfd8fc827" or fresh):
                    continue
            return lab
    return ""


def line_verdict(rs):
    """over all the line's days, the front seat first: FRONT-OPEN if the pools someone bought ahead of the fleet mostly still got the fleet
    and real outside buys got out at least as often as they were rugged (the 2.433 line); CLOSED if fronted pools mostly got no fleet buy
    (skipped or pulled: Base V2 on Oct 21); TRAP if real outside buys were pulled on unsold with no exit at least as often as they got out
    (the owner's rule: skip a line where an entry triggers the rug); TOLERANT with 3+ exits and at most a fifth rugged; UNTESTED with no
    real outside buy at all; MIXED otherwise"""
    so, ru = sum(r["sold"] for r in rs), sum(r["rugged"] for r in rs)
    came, none = sum(r["came"] for r in rs), sum(r["none"] for r in rs)
    if came >= 3 and came >= 3 * none and ru <= so:
        return "FRONT-OPEN"
    if none >= 2 and none >= came:
        return "CLOSED"
    if ru >= 1 and ru >= so:
        return "TRAP"
    if so >= 3 and ru <= 0.2 * (so + ru):
        return "TOLERANT"
    return "UNTESTED" if so + ru + sum(r["held"] for r in rs) == 0 else "MIXED"


def main(ch):
    here = os.path.dirname(os.path.abspath(__file__))
    rows = []
    for f in sorted(glob.glob(os.path.join(here, f"out/front_{ch}_2*.json"))):
        day = os.path.basename(f)[len(f"front_{ch}_"):-5]
        for name, t in json.load(open(f))["lines"].items():
            m = lambda k: st.median(t[k]) if t[k] else float("nan")
            rl = dict(t["real"])
            if t.get("rule") != "exit-window":
                print(f"   (stale run, re-run front.py: {os.path.basename(f)})"); continue
            rows.append({"day": day, "line": name, "n": t["n"], "verdict": t["verdict"], "seat1": m("seat1"), "seat3": m("seat3"),
                         "T": m("first"), "sold": rl.get("SOLD", 0), "rugged": rl.get("RUGGED", 0), "held": rl.get("HELD", 0),
                         "early_pnl": sum(v[2] for v in t["early"].values()), "known": label(ch, name, t.get("targets")),
                         "came": t["pre"].get("CAME", 0), "none": t["pre"].get("NONE", 0), "exit": t.get("real_exit", 0)})
    print(f"{ch}: {len(rows)} line-days from {len({r['day'] for r in rows})} days")
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["known"], r["line"])].append(r)
    cand = lambda r, lv: lv not in ("TRAP", "CLOSED") and (r["verdict"].startswith("TOLERANT") or (r["verdict"] in ("UNTESTED", "OPEN") and r["seat1"] >= 0.05))
    for title, keep in (("NEW lines (not in any earlier report)", lambda k: not k[0]), ("lines already documented", lambda k: bool(k[0]))):
        print(f"\n== {title}")
        for k, rs in sorted(by.items(), key=lambda kv: (-sum(cand(r, line_verdict(kv[1])) for r in kv[1]), -sum(r["n"] for r in kv[1]))):
            if not keep(k):
                continue
            lv = line_verdict(rs)
            print(f"  {k[1][:56]:56s} {k[0][:44]:44s} days {len(rs):3d} ({rs[0]['day'][:8]}..{rs[-1]['day'][:8]}) pools {sum(r['n'] for r in rs):6d} | {lv:8s}"
                  f" | real outside buys sold {sum(r['sold'] for r in rs)} rugged {sum(r['rugged'] for r in rs)}"
                  f" (with an exit window {sum(r['exit'] for r in rs)})"
                  f" | fronted: fleet came {sum(r['came'] for r in rs)} / none {sum(r['none'] for r in rs)}"
                  f" | seat1 median {st.median(r['seat1'] for r in rs if r['seat1'] == r['seat1']) if any(r['seat1'] == r['seat1'] for r in rs) else float('nan'):+.1%}")
            for r in rs:
                if cand(r, lv):
                    print(f"      candidate {r['day']} n {r['n']:4d} {r['verdict']:14s} T+{r['T']:<5g} seat1 {r['seat1']:+.1%} seat3 {r['seat3']:+.1%}"
                          f" | sold {r['sold']} rugged {r['rugged']} held {r['held']} | early outside pnl {r['early_pnl']:+.4f}")
    json.dump(rows, open(os.path.join(here, f"out/verdicts_{ch}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1])
