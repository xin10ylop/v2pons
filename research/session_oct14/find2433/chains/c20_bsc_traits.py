"""Traits of the BNB 2.433-shape line (c18 data): per pool the bot's first buy (offset, tolerance = minOut / output), the room a buy at
+1 leaves before the bot's first buy would fail, the theoretical front trade (buy at +1, sell right after the bot's first buy), decoys and
outsiders, the pull (offset, sender, selector), launches per hour and gas prices. Pure computation on cached rows."""
import sys, json, collections, statistics as st, time
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/v2pons/src')
import v4math
RC = "0x07cb61618b69234d954022ff738a015548715533"
L = json.load(open("c18_launches.json")); E = [json.loads(l) for l in open("c18_events_cache.jsonl")]
TX = {}
for l in open("c18_swaptx_cache.jsonl"):
    r = json.loads(l); TX[r["h"]] = r
def s256(x): return x - (1 << 256) if x >= (1 << 255) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
byid = collections.defaultdict(list)
for e in E: byid[e["id"]].append(e)
bot_wallets = set(TX[e["tx"]]["from"] for e in E if e["k"] == "swap" and e["tx"] in TX and TX[e["tx"]]["to"] == RC and TX[e["tx"]]["sel"] == "0xc1120e3d")
P = []
for r in L:
    ev = sorted(byid[r["id"]], key=lambda e: (e["b"], e["li"])); b0 = r["b"]; fee = 5000
    sp, liq = r["sqrtP"], r["liq"][0]
    rows = []; pull = None
    for e in ev:
        t = TX.get(e["tx"], {})
        if e["k"] == "liq":
            dl = s256(W(e["d"], 2))
            if dl < 0 and pull is None: pull = {"off": e["b"] - b0, "from": t.get("from"), "to": t.get("to"), "sel": t.get("sel")}
            continue
        a0, a1 = s256(W(e["d"], 0)), s256(W(e["d"], 1))
        cls = "BOT" if t.get("to") == RC and t.get("sel") == "0xc1120e3d" else ("BOTSELL" if t.get("from") in bot_wallets else "OTHER")
        rows.append({"off": e["b"] - b0, "b": e["b"], "ti": e["ti"], "cls": cls, "eth": -a0 / 1e18, "tok": a1, "sp_after": W(e["d"], 2), "L": W(e["d"], 3),
                     "from": t.get("from"), "to": t.get("to"), "sel": t.get("sel"), "v": t.get("v", 0), "gp": t.get("gp", 0),
                     "minOut": int(t["inp"][10 + 64 * 4: 10 + 64 * 5], 16) if cls == "BOT" and len(t.get("inp", "")) >= 10 + 64 * 5 else None})
    bots = [x for x in rows if x["cls"] == "BOT"]
    if not bots: P.append({"b0": b0, "nobot": True, "pull": pull}); continue
    fb = bots[0]; pre = [x for x in rows if (x["b"], x["ti"]) < (fb["b"], fb["ti"])]
    sp_pre = pre[-1]["sp_after"] if pre else sp
    q_pre = v4math.buy_out_int(sp_pre, liq, fb["v"], fee); q_init = v4math.buy_out_int(sp, liq, fb["v"], fee)
    tol_actual = fb["minOut"] / fb["tok"] if fb["tok"] else None
    # room: max X bought on the pre-bot state so that the bot's first buy still returns >= minOut
    lo, hi = 0, 10 ** 21
    for _ in range(80):
        m = (lo + hi) // 2
        out_us = v4math.buy_out_int(sp_pre, liq, m, fee)
        sp1 = int(v4math.sqrt_after_buy(sp_pre, liq, m - (m * fee + 999_999) // 1_000_000))
        if v4math.buy_out_int(sp1, liq, fb["v"], fee) >= fb["minOut"]: lo = m
        else: hi = m
    room = lo
    def front(X):
        tok = v4math.buy_out_int(sp_pre, liq, X, fee); sp1 = int(v4math.sqrt_after_buy(sp_pre, liq, X - (X * fee + 999_999) // 1_000_000))
        xb = fb["v"] - (fb["v"] * fee + 999_999) // 1_000_000; sp2 = int(v4math.sqrt_after_buy(sp1, liq, xb))
        return v4math.sell_out_int(sp2, liq, tok, fee) / X - 1
    others = [x for x in rows if x["cls"] == "OTHER"]
    P.append({"b0": b0, "v_launch": r["value"] / 1e18, "fb_off": fb["off"], "fb_ti_launch": (fb["off"], fb["ti"] - r["ti"]) if fb["off"] == 0 else None, "fb_v": fb["v"] / 1e18,
              "tol_actual": tol_actual, "tol_pre": fb["minOut"] / q_pre if q_pre else None, "tol_init": fb["minOut"] / q_init if q_init else None,
              "n_pre": len(pre), "pre": [(x["off"], x["cls"], round(x["eth"], 5), x["to"][:10] if x["to"] else None) for x in pre[:6]],
              "room": room / 1e18, "front_at_half_room": front(max(room // 2, 1)) if room > 10 ** 12 else None, "front_at_0.9room": front(int(room * 0.9)) if room > 10 ** 12 else None,
              "n_bot": len(bots), "bot_bnb": sum(x["v"] for x in bots) / 1e18, "n_botsell": sum(1 for x in rows if x["cls"] == "BOTSELL"),
              "others": [(x["off"], round(x["eth"], 5), x["from"][:10], x["to"][:10] if x["to"] else None, x["sel"]) for x in others[:8]], "n_others": len(others),
              "pull": pull, "bot_gp": st.median([x["gp"] for x in bots]) / 1e9})
json.dump(P, open("c20_bsc_traits.json", "w"), indent=1)
ok = [p for p in P if not p.get("nobot")]
pc = lambda v, q: sorted(v)[min(len(v) - 1, int(q * len(v)))] if v else None
print("pools", len(P), "with bot buys", len(ok), "bot wallets", len(bot_wallets))
for k in ["fb_off", "tol_actual", "tol_pre", "tol_init", "room", "front_at_half_room", "front_at_0.9room", "n_bot", "bot_bnb", "n_others", "n_pre", "bot_gp"]:
    v = [p[k] for p in ok if p.get(k) is not None]
    print(f"{k:20s} n={len(v):3d} p10/p50/p90 = {pc(v, .1)} / {pc(v, .5)} / {pc(v, .9)}")
print("first-buy offsets:", collections.Counter(p["fb_off"] for p in ok))
print("pull offsets:", sorted((p["pull"] or {}).get("off", -1) for p in P))
print("pull tx:", collections.Counter(((p["pull"] or {}).get("to"), (p["pull"] or {}).get("sel")) for p in P))
print("pre-bot swaps (first 10 pools):", [p["pre"] for p in ok[:10]])
print("outsiders (pools with any):", [(p["b0"], p["others"][:4], (p["pull"] or {}).get("off")) for p in ok if p["n_others"]][:20])
