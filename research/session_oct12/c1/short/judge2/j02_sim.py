"""Judge 2, step 2: engine-exact replay of the c1 family's short exits (offline: ../s02_pools.json as data, router calldata from the tx caches).

The model is j01_engine.py's (it rebuilds the engine's minOut of all 8 real attempts to the wei):
  trigger    the first router buy call (calldata word 2) of >= 0.005 ETH; fired only if its offset from the launch is <= max_blocks;
  minOut     int(buy_out_int(copy at the trigger, L, stake, 100) x 0.97), copy = launch state + every buy the feed shows (sells never);
  our buy    lands at the TOP of block T + dB (dB 2: 7 of our 8 attempts; dB 3 stress; dB 7 once, the 20:59 revert); it reverts when the
             real pool gives fewer tokens than minOut, or when the pool was pulled before its block;
  hold N     the sell is sent after the feed shows block B + N and lands at the top of B + N + lag (lag 1 or 2: our 7 sells; 3 stress);
  tp, cap C  take_profit on every buy the feed shows from our buy to the end of block B + C, on the copy (our stake in it, feed_tokens
             from the copy, 250k gas at 0.02 gwei); the first >= tp sends the sell in that block (lands + lag); else B + C as hold C;
  pulled     -100% when the launch wallet's pull is in a block before the landing block; a pull IN the landing block is counted
             as before our sell (conservative; our sells land at tx index 1-2), and flagged.
Our own real swaps are taken out of our 5 pools and our buy re-inserted where the scenario puts it.
Writes j02_sim.json: per pool, its regime and per scenario the outcome of every exit."""
from j01_engine import *
import calendar

HOLDS = [10, 15, 20, 25, 30, 35, 40, 60]
TPS = [0.04, 0.06]; CAPS = [30, 40]
EXITS = [("hold", n, None) for n in HOLDS] + [("tp", c, tp) for c in CAPS for tp in TPS]
EN = lambda e: f"hold {e[1]}" if e[0] == "hold" else f"tp {round(e[2] * 100)}% cap {e[1]}"
STAKE = 2 * 10 ** 15                                        # $5 at $2,500
GAS_RT = 20_000_000 * 250_000                               # the engine's round_trip_gas_wei at 0.02 gwei
SCEN = [(2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3), (7, 2)]
BD = "0xbd9dc5f684ed24f4a06559ff9dc736748cbbbc41"; T1315 = calendar.timegm((2026, 10, 12, 13, 15, 0))
HEAD = D["head"]
net = lambda x, f: x - (x * f + 999_999) // 1_000_000


def sp_swap(sp, s):
    """a recorded swap replayed at its exact input and its own fee field (the PoolManager's rounding)"""
    L = s["liq"]
    if L <= 0: return sp
    if s["buy"]:
        x = net(s["eth_wei"], s["fee"]); den = L + (x * sp) // Q96; return (L * sp + den - 1) // den
    return sp + (net(s["tok"], s["fee"]) * Q96) // L


Q96 = 1 << 96


def regime(p, Toff):
    """ours / holder (early: first held outside buy >= 0.001 ETH at <= T+5, before T included; later) / sold / none; bd13 flag. The
    analyst's c11 rule (an outsider >= 0.001 ETH bought from the launch to T+62 and did not sell by min(T+62, pull)), on the engine's T"""
    bd = p["ts"] >= T1315 and any(s["buy"] and s.get("from") == BD and s["eth"] >= 0.001 and (not p["pullpos"] or (s["bn"], s["li"]) < tuple(p["pullpos"])) for s in p["sw"])
    if any(s["cls"] == "ours" and s["buy"] for s in p["sw"]): return "ours", None, bd, None
    end = min(Toff + 62, p["pull"] if p["pull"] is not None else 1 << 40); hs, sold = [], []
    for s in p["sw"]:
        if not (s["buy"] and s["cls"] in ("recurring", "oneoff") and s["eth"] >= 0.001 and s["off"] <= Toff + 62): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        out = any((not x["buy"]) and x.get("from") == s.get("from") and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end for x in p["sw"])
        (sold if out else hs).append(s)
    if hs: return "holder", ("early" if hs[0]["off"] - Toff <= 5 else "later"), bd, hs[0]
    if sold: return "sold", None, bd, sold[0]
    return "none", None, bd, None


def simulate(p, trig, dB, lag, stake=STAKE):
    sw = [s for s in p["sw"] if s["cls"] != "ours"]
    k0, ts_, cpt = trig; Tb = ts_["bn"]; B = Tb + dB
    pullb = p["pullpos"][0] if p["pullpos"] else None
    min_out = int(v4math.buy_out_int(int(cpt), LIQ, stake, FEE) * (1 - SLIP))
    if pullb is not None and pullb < B: return {"fill": False, "why": "pulled before our buy"}
    st = None; i_ins = 0
    for k, s in enumerate(sw):
        if s["bn"] < B: st = s; i_ins = k + 1
        else: break
    sp0, L0, f0 = (st["sqrtP"], st["liq"], st["fee"]) if st else (p["launch_sqrtP"], LIQ, FEE)
    tokens = v4math.buy_out_int(sp0, L0, stake, f0)
    if tokens < min_out: return {"fill": False, "why": "minOut", "short": tokens / min_out - 1}
    # the copy at our landing (every seen buy in the blocks before B), feed_tokens, then our stake in it (live: apply_buy)
    cp = float(p["launch_sqrtP"]); done = set()
    for s in sw[:i_ins]:
        a = seen(p, s)
        if a is None or a[1] is None or s["tx"] in done: continue
        done.add(s["tx"]); cp = v4math.sqrt_after_buy(cp, LIQ, net(a[1], FEE))
    feed_tokens = v4math.buy_out_int(int(cp), LIQ, stake, FEE); cp = v4math.sqrt_after_buy(cp, LIQ, net(stake, FEE))
    # the real pool with our buy in, then every later swap at its own size
    x = net(stake, f0); den = L0 + (x * sp0) // Q96; sp = (L0 * sp0 + den - 1) // den
    path = [(B, sp, L0, f0)]; tpev = []
    for s in sw[i_ins:]:
        if s["bn"] > B + 80: break
        if pullb is not None and s["bn"] >= pullb and s["liq"] <= 0: break
        sp = sp_swap(sp, s); path.append((s["bn"], sp, s["liq"], s["fee"]))
        a = seen(p, s)
        if a is not None and a[1] is not None and s["tx"] not in done:
            done.add(s["tx"]); cp = v4math.sqrt_after_buy(cp, LIQ, net(a[1], FEE))
            tpev.append((s["bn"], (v4math.sell_out_int(int(cp), LIQ, feed_tokens, FEE) - stake - GAS_RT) / stake))

    def land(X):
        if pullb is not None and pullb <= X: return -1.0, True, pullb == X
        stt = path[0]
        for y in path:
            if y[0] < X: stt = y
            else: break
        _, s_, L_, f_ = stt
        if L_ <= 0: return -1.0, True, False
        return v4math.sell_out_int(s_, L_, tokens, f_) / stake - 1, False, False
    res = {}
    for e in EXITS:
        kind, n, tp = e; send = B + n; why = "deadline"
        if kind == "tp":
            for bn, r in tpev:
                if bn > B + n: break
                if r >= tp: send = bn; why = "tp"; break
        g, pulled, same = land(send + lag)
        res[EN(e)] = (g, pulled, send - B, send + lag - B, why, same)
    return {"fill": True, "res": res, "B": B, "pull_after_buy": None if pullb is None else pullb - B}


if __name__ == "__main__":
    rows = []; skip = collections.Counter()
    for p in sorted(P, key=lambda q: q["ts"]):
        if p["launch_sqrtP"] != SQRTP or p["ml"][0]["liq"] != LIQ: skip["not the family's launch (pin: not armed)"] += 1; continue
        cp, trig = engine_copy(p)
        if trig is None: skip["no router buy >= 0.005 ETH"] += 1; continue
        k0, ts_, cpt = trig; Toff = ts_["off"]
        if p["pull"] is not None and p["pull"] < Toff: skip["pulled before the trigger"] += 1; continue
        if HEAD - p["lb"] < Toff + 75: skip["too young to see T + 75"] += 1; continue
        g, sub, bd, hb = regime(p, Toff)
        row = {"pid": p["pid"], "ts": p["ts"], "lb": p["lb"], "T": Toff, "T_analyst": p["T"], "T_eth": ts_["eth_wei"], "group": g, "sub": sub, "bd13": bd,
               "holder_buy": None if hb is None else {"off": hb["off"], "from": hb["from"], "eth": hb["eth"]},
               "pull": p["pull"], "sc": {}}
        for dB, lag in SCEN:
            row["sc"][f"{dB}|{lag}"] = simulate(p, trig, dB, lag)
        rows.append(row)
    json.dump({"rows": rows, "exits": [EN(e) for e in EXITS], "scen": [f"{a}|{b}" for a, b in SCEN]}, open(JD("j02_sim.json"), "w"))
    print(f"pools with an engine trigger, usable: {len(rows)}; left out: {dict(skip)}")
    print("groups (all T):", dict(collections.Counter((r["group"], r["sub"], r["bd13"]) for r in rows)))
    print("T offsets: engine T differs from the analyst's T in", sum(r["T"] != r["T_analyst"] for r in rows), "pools;",
          "engine T > 400:", sum(r["T"] > 400 for r in rows), "; > 100:", sum(r["T"] > 100 for r in rows))
    for r in rows:
        if r["T"] != r["T_analyst"]: print(f"   {r['pid'][:10]} analyst T +{r['T_analyst']} -> engine T +{r['T']} ({r['T_eth'] / 1e18:.4f} ETH) {r['group']}")
    b = rows and [r for r in rows if r["group"] == "ours"]
    print("\nour 5 fills at dB 2 lag 2, hold 60 (real: +4.02 / +6.66 / -0.01 / +3.46 / -100):",
          [round(r["sc"]["2|2"]["res"]["hold 60"][0] * 100, 2) if r["sc"]["2|2"]["fill"] else "revert" for r in b],
          "lag 1:", [round(r["sc"]["2|1"]["res"]["hold 60"][0] * 100, 2) if r["sc"]["2|1"]["fill"] else "revert" for r in b])
    rev = [r for r in rows if r["pid"][:10] in ("0x35869115", "0xd4654e14", "0x266d00f1")]
    print("our 3 reverted attempts, model at dB 2:", [(r["pid"][:10], r["sc"]["2|2"]["fill"], round(r["sc"]["2|2"].get("short", 0) * 100, 2)) for r in rev],
          "dB 7:", [(r["pid"][:10], r["sc"]["7|2"]["fill"], round(r["sc"]["7|2"].get("short", 0) * 100, 2)) for r in rev])
