#!/usr/bin/env python3
"""line_adapt trap test. Outsider = a buyer that never bought through the bot's router (c1120e3d) in any pool, buying at least 1e-5 ETH (the
0xe71a69f4 dust bot buys 2e-6). For every v3.0/v5.0 pool of the 24 h (complete windows):
  1. outsider buys BEFORE the bot's first buy, by offset band (+1..+3, +4..+7, +8..+25 = the delayed front's entry), with what followed:
     the pull before any bot buy / at bot+2..4 / later or never, and the pull's delay after the outsider's buy;
  2. outsider buys AFTER the bot's first buy (the ride's position): the pull's delay after that buy vs the same delay measured from the
     same offset in pools of the same regime without such a buy (control).
-> trap.json, printed"""
import os, json, time, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
NEW_FROM = int(time.mktime(time.strptime("2026-10-11 04:22:19", "%Y-%m-%d %H:%M:%S"))) - time.timezone
REACT_FROM = int(time.mktime(time.strptime("2026-10-11 04:17:00", "%Y-%m-%d %H:%M:%S"))) - time.timezone
R = [r for r in json.load(open(os.path.join(D, "rec.json"))) if r["complete"]]
botw = {s["from"] for r in R for s in r["swaps"] if s["bot"]}
MIN = int(1e13)
# the operator's own small buyers (HANDOFF section 1, 16.10) and the dust bots: not outsiders for the reaction test
OPS = {"0x93b0790287720a922bb7e3cf0712062c1669847d", "0xb4c345dcf30be7ef93abbacb5f67bd3cc3dfaa04", "0xe71a69f434a719cd5afa411568b69716aab3b84a",
       "0xe74fcc81553c2b1102accdfaafa663418119098d"}
MIN_AFTER = int(1e14)                                                                    # after the bot's buy: a real-size outsider, 0.0001 ETH or more
out = {"before_bot": [], "after_bot": [], "control": {}}
for r in R:
    sw = sorted(r["swaps"], key=lambda s: (s["off"], s["li"]))
    fb = next((s for s in sw if s["bot"] and s["side"] == "B"), None)
    pull = r["pull"]; po = pull["off"] if pull else None
    reg = "new" if r["ts0"] >= NEW_FROM else ("react" if r["ts0"] >= REACT_FROM else "old")
    for s in sw:
        if s["side"] != "B" or s["from"] in botw or s["from"] in OPS or -s["a0"] < MIN: continue
        if pull and (s["off"], s["li"]) > (pull["off"], pull["li"]): continue
        before = fb is None or (s["off"], s["li"]) < (fb["off"], fb["li"])
        row = {"t": time.strftime("%m-%d %H:%M:%S", time.gmtime(r["ts0"])), "fam": r["fam"], "reg": reg, "pid": r["pid"][:12], "off": s["off"], "eth": round(-s["a0"] / 1e18, 7),
               "from": s["from"], "to": s["to"], "bot_off": fb["off"] if fb else None, "pull_off": po, "pull_after_buy": (po - s["off"]) if po is not None else None,
               "early_pull": bool(pull and (fb is None or (pull["off"], pull["li"]) < (fb["off"], fb["li"])))}
        if before:
            row["band"] = "+1..+3" if s["off"] <= 3 else ("+4..+7" if s["off"] <= 7 else ("+8..+25" if s["off"] <= 25 else "+26.."))
            out["before_bot"].append(row)
        elif -s["a0"] >= MIN_AFTER:
            row["after_bot"] = s["off"] - fb["off"]
            out["after_bot"].append(row)
# control for the ride: pools of the regime with no outsider buy after the bot: the share pulled within 20/40 blocks of a random block after the bot
import random
random.seed(7)
ab_pids = {x["pid"] for x in out["after_bot"]}
for fam in ("v3.0", "v5.0"):
    for reg in ("old", "new"):
        C = []
        for r in R:
            if r["fam"] != fam or (("new" if r["ts0"] >= NEW_FROM else "old") != reg) or r["pid"][:12] in ab_pids: continue
            fb = next((s for s in r["swaps"] if s["bot"] and s["side"] == "B"), None)
            if not fb: continue
            C.append((r["pull"]["off"] - fb["off"]) if r["pull"] else None)
        n = len(C); pulled = sorted(c for c in C if c is not None)
        # matched: for each outsider row of this fam/regime, the same offset after the bot in every control pool: pulled within 20 / 40 blocks after it?
        rows_fr = [x for x in out["after_bot"] if x["fam"] == fam and x["reg"] == reg]
        m20 = m40 = mn = 0
        for x in rows_fr:
            for c in C:
                if c is not None and c <= x["after_bot"]: continue            # control pool already pulled by then
                mn += 1
                if c is not None and c - x["after_bot"] <= 20: m20 += 1
                if c is not None and c - x["after_bot"] <= 40: m40 += 1
        out["control"][f"{fam}|{reg}|matched"] = {"pairs": mn, "pulled_within_20_after": round(m20 / mn, 4) if mn else None, "pulled_within_40_after": round(m40 / mn, 4) if mn else None}
        out["control"][f"{fam}|{reg}"] = {"n": n, "pulled_within_1200": len(pulled), "pull_minus_bot_p10_50_90": [pulled[int(k * (len(pulled) - 1))] for k in (0.1, 0.5, 0.9)] if pulled else None,
                                         "pulled_within_bot+40": sum(1 for c in pulled if c <= 40), "pulled_within_bot+100": sum(1 for c in pulled if c <= 100)}
json.dump(out, open(os.path.join(HERE, "trap.json"), "w"), indent=0)
print("== outsider buys before the bot's first buy (band, regime, reaction):")
t = collections.defaultdict(collections.Counter)
for x in out["before_bot"]:
    react = "pulled_before_bot" if x["early_pull"] else ("pull_bot+2..4" if x["pull_off"] is not None and x["bot_off"] is not None and x["pull_off"] - x["bot_off"] <= 4 else "none_or_later")
    t[(x["fam"], x["reg"], x["band"])][react] += 1
for k in sorted(t): print("  ", k, dict(t[k]))
print("  delayed-front band (+8..+25) rows:"); [print("    ", x) for x in out["before_bot"] if x["band"] in ("+8..+25", "+26..")]
print("  new/react regime rows:"); [print("    ", x) for x in out["before_bot"] if x["reg"] != "old"]
print("== real-size outsider buys (>= 0.0001 ETH, not the operator's decoys) after the bot's first buy:", len(out["after_bot"]))
for x in out["after_bot"]: print("    ", x["t"], x["fam"], x["reg"], x["pid"], "off", x["off"], "after_bot", x["after_bot"], "eth", x["eth"], x["from"][:10], "->", (x["to"] or "")[:10], "pull_after_buy", x["pull_after_buy"])
by = collections.defaultdict(list)
for x in out["after_bot"]: by[(x["fam"], x["reg"])].append(x)
for k, v in sorted(by.items()):
    v = [x for x in v if x["reg"] != "react"]
    if not v: continue
    pa = sorted(x["pull_after_buy"] for x in v if x["pull_after_buy"] is not None)
    print("  ", k, "n", len(v), "pools", len({x['pid'] for x in v}), "senders", collections.Counter(x["from"][:10] for x in v).most_common(6),
          "eth p50", sorted(x["eth"] for x in v)[len(v) // 2], "after_bot p50", sorted(x["after_bot"] for x in v)[len(v) // 2],
          "pulled", len(pa), "pull after buy p10/50/90", [pa[int(q * (len(pa) - 1))] for q in (0.1, 0.5, 0.9)] if pa else None, "<=20", sum(1 for a in pa if a <= 20), "<=40", sum(1 for a in pa if a <= 40))
print("== control (no outsider after the bot):", json.dumps(out["control"]))
