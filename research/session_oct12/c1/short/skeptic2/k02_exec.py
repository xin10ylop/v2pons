"""Skeptic 2, execution lens: the short exits re-measured with my own replay and the engine's own execution (offline: the analyst's
s02_pools.json is used as DATA only (swaps, their transactions, the pulls); the router calldata from ../../c03_txs.jsonl and ../s01_txs_new.jsonl).

Execution model (flip_engine.py, read for this):
  * trigger: the first router call (to 0xd6d35b56, a buy) of >= min_eth 0.005 ETH within max_blocks 400 of the launch; its amount is the
    calldata word 2 (value_word), checked against the Swap log;
  * the engine's price copy (p["sp"]): the family's launch sqrtP and L, every buy the feed shows applied (router calls by their calldata amount,
    a stranger's ETH-value buy by its tx value), sells never;
  * our buy: minOut = int(buy_out_int(copy at the trigger, L, stake, 100) x (1 - BUY_SLIP 0.03)); it lands dB blocks after the trigger block
    (dB 2 = all 8 of our attempts that were sent on time; dB 3 as the stress), at the TOP of its block (all 5 real fills: tx index 1) or at
    the END of it (the analyst's 'last price at or before T+2'); it REVERTS (gas only, no position) when the pool gives fewer tokens than
    minOut (3 of our 8 attempts did), or when the pool is pulled at or before its block;
  * the feed sees our buy: feed_tokens = buy_out_int(copy, L, stake, 100), then apply_buy(stake);
  * take-profit tp: on every buy the feed shows behind ours (its block <= our buy + cap), ret = (sell_out_int(copy) - stake - 250,000 x
    0.02 gwei) / stake; the first ret >= tp sends the sell in that block; else the deadline sends it at the end of block buy + N (send_after =
    hold_blocks); the sell lands LAG blocks later (LAG 1, 2, 3; ours: 1 of 4 at 1, 3 of 4 at 2, every reverted attempt's sell at 2), at the top of
    its block (ours: idx 1-2, once 44); its ETH = sell_out_int on the REAL pool (our buy in it, every recorded swap replayed at its own size and
    fee) after the swaps before it;
  * -100% when the launch wallet's pull lands in or before the sell's block (the same-block case counted as pulled; the alternative is reported).
Gas (k01_gas.json, our own receipts): a filled round trip 4.32e-6 ETH, a fill whose sell hit the pull 8.82e-6 ETH (the 335k-gas sell), a
reverted attempt (buy + its presigned sell) 1.82e-6 ETH.
Writes k02_exec.json (per pool, per scenario, per exit: outcome)."""
from sk import *
import collections, calendar
Q96 = 1 << 96; FEE = 100; SLIP = 0.03; MIN_TRIG = 5 * 10 ** 15; MAX_BLOCKS = 400; GAS_RT_COPY = 20_000_000 * 250_000
HOLDS = [5, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60]
TPS = [0.01, 0.02, 0.03, 0.04, 0.06, 0.08]; CAPS = [10, 15, 20, 25, 30, 40, 45, 50, 60]
EXITS = [("hold", n, None) for n in HOLDS] + [("tp", c, tp) for c in CAPS for tp in TPS]
ENAME = lambda e: f"hold {e[1]}" if e[0] == "hold" else f"tp {round(e[2] * 100)}% cap {e[1]}"
STAKES = {"0.002": 2 * 10 ** 15, "0.0058": 58 * 10 ** 14}
SCEN = [(dB, place, lag) for dB in (2, 3) for place in ("top", "end") for lag in (1, 2, 3)]
BD = "0xbd9dc5f684ed24f4a06559ff9dc736748cbbbc41"; T1315 = calendar.timegm((2026, 10, 12, 13, 15, 0))

def netx(x, fee): return x - (x * fee + 999_999) // 1_000_000
def sp_after(sp, L, s):
    """one recorded swap replayed at its own exact input and fee (the PoolManager's rounding)"""
    if s["buy"]:
        x = netx(s["eth_wei"], s["fee"]); den = L + (x * sp) // Q96; return (L * sp + den - 1) // den
    return sp + (netx(s["tok"], s["fee"]) * Q96) // L
def sp_after_eth(sp, L, eth, fee):
    x = netx(eth, fee); den = L + (x * sp) // Q96; return (L * sp + den - 1) // den

D = json.load(open(SH("s02_pools.json"))); P = D["pools"]; HEAD = D["head"]
RIN = {}
for f in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl")):
    for l in open(f):
        t = json.loads(l)
        if t["to"] == ROUTER: RIN[t["hash"]] = t["input"]
word = lambda inp, i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)

def check0():
  """(0) checks: my replay against every recorded sqrtP; the router's calldata amount against its Swap log"""
  nchk = bad = 0; amt_ok = amt_bad = 0
  for p in P:
    sw = p["sw"]
    for a, b in zip(sw, sw[1:]):
        if b["liq"] <= 0 or a["liq"] != b["liq"]: continue
        nchk += 1
        if sp_after(a["sqrtP"], b["liq"], b) != b["sqrtP"] and abs(sp_after(a["sqrtP"], b["liq"], b) - b["sqrtP"]) > b["sqrtP"] * 1e-12: bad += 1
    for s in sw:
        if s["buy"] and s.get("to") == ROUTER and s["tx"] in RIN:
            inp = RIN[s["tx"]]
            if word(inp, 2) == s["eth_wei"] and word(inp, 7) == 0: amt_ok += 1
            else: amt_bad += 1
  print(f"(0) replay: {nchk} consecutive swaps, {bad} differ from the chain by > 1e-12; router buys: calldata word 2 == Swap ETH and flag 0 in {amt_ok}, not in {amt_bad}")

def seen_amount(s):
    """what the engine's copy applies for this swap (None: the feed does not see it as a buy)"""
    if not s["buy"]: return None
    if s.get("to") == ROUTER:
        inp = RIN.get(s["tx"]); return word(inp, 2) if inp else s["eth_wei"]
    if s["cls"] == "ours": return None                       # our own buy is applied by our_buy_landed
    v = s.get("value") or 0
    return v if v > 0 else None

def classify(p):
    """the analyst's regimes, recomputed: ours / holder (early: first held >= 0.001 ETH outside buy at <= T+5; later) / sold / none; bd13"""
    T = p["T"]
    if any(s["cls"] == "ours" and s["buy"] for s in p["sw"]): g, sub = "ours", None
    else:
        end = min(T + 62, p["pull"] if p["pull"] is not None else 1 << 40); hs, sold = [], []
        for s in p["sw"]:
            if not (s["buy"] and s["cls"] in ("recurring", "oneoff") and s["eth"] >= 0.001 and s["off"] <= T + 62): continue
            if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
            sl = any((not x["buy"]) and x.get("from") == s.get("from") and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end for x in p["sw"])
            (sold if sl else hs).append(s)
        if hs: g, sub = "holder", ("early" if hs[0]["off"] - T <= 5 else "later")
        elif sold: g, sub = "sold", None
        else: g, sub = "none", None
    bd = p["ts"] >= T1315 and any(s["buy"] and s.get("from") == BD and s["eth"] >= 0.001 and (not p["pullpos"] or (s["bn"], s["li"]) < tuple(p["pullpos"])) for s in p["sw"])
    return g, sub, bd

def simulate(p, stake, dB, place, lag, check=True):
    """one attempt on pool p: returns {"fill": bool, "why", per exit: (gross, pulled, send_off)}"""
    sw = [s for s in p["sw"] if s["cls"] != "ours"]          # our real swaps out: our buy is re-inserted where the scenario puts it
    lb = p["lb"]; pullb = p["pullpos"][0] if p["pullpos"] else None
    # the engine's copy up to the trigger, and the trigger itself
    copy = float(p["launch_sqrtP"]); trig = None
    for k, s in enumerate(sw):
        a = seen_amount(s)
        if a is None: continue
        copy = v4math.sqrt_after_buy(copy, LIQ, netx(a, FEE))
        if s.get("to") == ROUTER and a >= MIN_TRIG:
            trig = (k, s); break
    if trig is None or trig[1]["off"] > MAX_BLOCKS: return {"fill": False, "why": "no trigger"}
    k0, ts = trig; Tb = ts["bn"]
    min_out = int(v4math.buy_out_int(int(copy), LIQ, stake, FEE) * (1 - SLIP))
    B = Tb + dB
    if pullb is not None and pullb <= B: return {"fill": False, "why": "pulled before our buy"}
    # the real pool just before our buy (top: before every swap of block B; end: after them) and the copy the feed has then
    sp = L = fee = None; i_ins = 0; copy_at = float(p["launch_sqrtP"])
    for k, s in enumerate(sw):
        if s["bn"] < B or (place == "end" and s["bn"] == B):
            sp, L, fee = s["sqrtP"], s["liq"], s["fee"]; i_ins = k + 1
            a = seen_amount(s)
            if a is not None: copy_at = v4math.sqrt_after_buy(copy_at, LIQ, netx(a, FEE))
        else: break
    tokens = v4math.buy_out_int(sp, L, stake, fee)
    if check and tokens < min_out: return {"fill": False, "why": "minOut (BUY_SLIP 3%)", "short": round(tokens / (min_out / (1 - SLIP)) - 1, 4)}
    feed_tokens = v4math.buy_out_int(int(copy_at), LIQ, stake, FEE); copy_at = v4math.sqrt_after_buy(copy_at, LIQ, netx(stake, FEE))
    # the real path with our buy in, and the copy's take-profit returns at each seen buy behind ours
    sp = sp_after_eth(sp, L, stake, fee); base = (sp, L, fee); path = []; tpev = []; c = copy_at          # base: the pool right after our buy
    for s in sw[i_ins:]:
        if s["bn"] > B + 75: break
        if s["liq"] > 0: sp = sp_after(sp, s["liq"], s)
        path.append((s["bn"], sp, s["liq"], s["fee"]))
        a = seen_amount(s)
        if a is not None:
            c = v4math.sqrt_after_buy(c, LIQ, netx(a, FEE))
            tpev.append((s["bn"], (v4math.sell_out_int(int(c), LIQ, feed_tokens, FEE) - stake - GAS_RT_COPY) / stake))
    def at(X):
        """the pool (our buy in) after every swap of the blocks before X: our sell at the top of block X"""
        st = None
        for x in path:
            if x[0] < X: st = x
            else: break
        return st
    def ret_landing(X):
        if pullb is not None and pullb <= X: return -1.0, True
        st = at(X); s_, L_, f_ = (base if st is None else st[1:])
        if L_ <= 0: return -1.0, True
        return v4math.sell_out_int(s_, L_, tokens, f_) / stake - 1, False
    res = {}
    for e in EXITS:
        kind, n, tp = e
        send = B + n
        if kind == "tp":
            for bn, r in tpev:
                if bn > B + n: break
                if pullb is not None and bn > pullb: break
                if r >= tp: send = bn; break
        g, pulled = ret_landing(send + lag)
        res[ENAME(e)] = (g, pulled, send - B)
    return {"fill": True, "res": res, "pull_after_buy": None if pullb is None else pullb - B, "trig_off": ts["off"]}

def main():
  check0()
  rows = []; skipped = collections.Counter()
  for p in sorted(P, key=lambda p: p["ts"]):
      if p["T"] is None: skipped["no trigger"] += 1; continue
      if p["launch_sqrtP"] != SQRTP or not p["sw"] or p["sw"][0]["liq"] != LIQ: skipped["not the family's launch state"] += 1; continue
      if HEAD - p["lb"] < p["T"] + 70: skipped["too young"] += 1; continue
      g, sub, bd = classify(p)
      if g == "sold": skipped["an outsider >= 0.001 sold again by T+62"] += 1; continue
      row = {"pid": p["pid"], "ts": p["ts"], "T": p["T"], "group": g, "sub": sub, "bd13": bd, "pull_T": None if p["pull"] is None else p["pull"] - p["T"],
             "router_buys_T1": sum(1 for s in p["sw"] if s["buy"] and s.get("to") == ROUTER and p["T"] <= s["off"] <= p["T"] + 1), "sc": {}}
      for sk_, st in STAKES.items():
          for dB, place, lag in SCEN:
              row["sc"][f"{sk_}|{dB}|{place}|{lag}"] = simulate(p, st, dB, place, lag)
          row["sc"][f"{sk_}|analyst"] = simulate(p, st, 2, "end", 2, check=False)                  # the analyst's setting: end of T+2, no minOut, lag 2
      rows.append(row)
  print(f"pools simulated {len(rows)}; left out {dict(skipped)}")
  print("groups:", collections.Counter((r["group"], r["sub"], r["bd13"]) for r in rows))
  json.dump({"rows": rows, "exits": [ENAME(e) for e in EXITS], "scen": [f"{a}|{b}|{c}" for a, b, c in SCEN], "stakes": list(STAKES)}, open(K("k02_exec.json"), "w"))

  # ---- (1) validation: our 8 real attempts (5 fills, 3 reverts) under the model, and our real gross
  print("\n(1) our 8 real attempts under the model (0.002 ETH, dB 2, top):")
  ours_rev = {"0x35869115", "0xd4654e14", "0x266d00f1"}
  for r in rows:
      if r["group"] == "ours" or r["pid"][:10] in ours_rev:
          x = r["sc"]["0.002|2|top|2"]
          print(f"   {utc(r['ts'])} {r['pid'][:10]} {r['group']:6s} real: {'FILL' if r['group'] == 'ours' else 'REVERT'}; model: {'FILL' if x['fill'] else 'REVERT (' + x['why'] + (', ' + format(x.get('short', 0), '+.2%') if 'short' in x else '') + ')'}"
                + (f"; hold 60 lag 2 {x['res']['hold 60'][0]:+.2%}, lag 1 {r['sc']['0.002|2|top|1']['res']['hold 60'][0]:+.2%}" if x["fill"] else "")
                + f"; router buys in [T, T+1]: {r['router_buys_T1']}")

if __name__ == "__main__":
    main()
