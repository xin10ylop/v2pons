"""Judge 2, step 1: the engine's own c1 execution, rebuilt from src/flip_engine.py (release 0.9) and checked against our 8 real attempts.

What the engine does for a wave family (c1), read for this (line numbers of src/flip_engine.py at e132471):
  arm_front 1219        the launch (PositionManager multicall 0xac9650d8, 2,276 bytes, value 0) is armed from its calldata only when its fee,
                        tick spacing, sqrtP and liquidity match the family ("pin": true: a new fingerprint is not armed at all);
  on_wave_call 2590     every value-0 call to the router 0xd6d35b56, selector e6cb474f, token in word 8, flag word 7 == 0 (a buy): apply_buy
                        (the price copy) with the calldata word 2 amount; the FIRST of >= min_eth (0.005) is the trigger, fired in its block
                        when its offset from the launch is <= max_blocks (else "late"); a reverted router call shows in the feed too;
  on_front_buy 2384     a stranger's ETH-value transaction carrying the token: apply_buy with the tx value, no trigger; then take_profit;
  _fire 1682-1698       hold = send_after = hold_blocks (front: no SELL_LEAD); minOut = int(buy_out_int(copy, L, stake, fee) x 0.97); the
                        buy (relay buy(..., stake, minOut, deadline = trigger ts + 3 s)) and the sell (minOut 0) are signed together;
  our_buy_landed 2313   when the feed shows our buy (block B): feed_tokens = buy_out_int(copy, ...), then apply_buy(stake) (live);
  ingest 2713           the sell is sent once the feed shows block >= B + hold_blocks (after that block's transactions): it lands at
                        B + hold + 1 or + 2 (our 7 sells with hold 60: + 61 once, + 62 six times);
  take_profit 2327      on every buy the feed shows behind ours (router call or stranger ETH buy, not stale, sell not yet sent):
                        (sell_out_int(copy, L, feed_tokens, 100) - stake - base_fee x 250,000) / stake >= tp sends the sell at once;
  _settle 1958-2034     pull check (ModifyLiquidity < 0 at (block, index) before our sell's): the family's halt (HALTED.front.c1); a family
                        nonbot_halt 0 turns the flat-trade streak halt off (pos["nonbot_halt"] = 0 is falsy: line 2020).
This script checks the fill model on our 8 attempts: the minOut word of each of our real buy transactions against the engine copy rebuilt
from the chain (router calldata amounts, strangers' tx values, sells never), and the real fill (or revert) against minOut."""
from jc import *
import collections

D = json.load(open(SH("s02_pools.json"))); P = D["pools"]
TX = {}
for f in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl")):
    for l in open(f):
        t = json.loads(l); TX[t["hash"]] = t
OURS = json.load(open(J("c04_ours.json")))
FEE = 100; SLIP = 0.03; MIN_TRIG = 5 * 10 ** 15
wd = lambda inp, i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def seen(p, s):
    """(kind, amount) the feed shows for this swap's transaction, or None: router buy by calldata word 2 (flag 0, token in word 8),
    a stranger's ETH-value tx carrying the token by its value; our own relay is applied separately"""
    if not s["buy"] or s["cls"] == "ours": return None
    t = TX.get(s["tx"])
    if s.get("to") == ROUTER:
        if t is None: return ("router?", s["eth_wei"])
        inp = t["input"]
        if inp[2:10] != "e6cb474f" or wd(inp, 7) != 0 or ("%064x" % wd(inp, 8))[-40:] != p["token"][2:]: return ("router-other", None)
        return ("router", wd(inp, 2))
    v = (t or {}).get("value", s.get("value") or 0)
    if not v: return None
    if t is not None and p["token"][2:] not in t["input"].lower(): return ("hidden", None)          # the feed cannot tie it to the pool
    return ("eth", v)


def engine_copy(p, upto=None):
    """walk the pool's swaps in chain order as the feed shows them: the copy (float sqrtP, as p["sp"]) and the trigger. Each transaction
    is applied once (a tx with two swaps on the pool carries one amount). upto: stop before this (bn, li)"""
    cp = float(p["launch_sqrtP"]); trig = None; done = set()
    for k, s in enumerate(p["sw"]):
        if upto is not None and (s["bn"], s["li"]) >= upto: break
        a = seen(p, s)
        if a is None or a[1] is None or s["tx"] in done: continue
        done.add(s["tx"]); cp = v4math.sqrt_after_buy(cp, LIQ, a[1] - (a[1] * FEE + 999_999) // 1_000_000)
        if trig is None and a[0] in ("router", "router?") and a[1] >= MIN_TRIG:
            trig = (k, s, cp)
            if upto is None: break
    return cp, trig


if __name__ == "__main__":
    # ---- our 8 attempts: the buy transactions (5 filled ones from the swap records, 3 reverted from c04)
    att = []
    for p in P:
        for s in p["sw"]:
            if s["cls"] == "ours" and s["buy"]:
                att.append((p, TX[s["tx"]], True, s))
    byhash = {o["hash"]: o for o in OURS}
    for o in OURS:
        if o["input"].startswith("0x5ed06f60") and o.get("c1"):
            p = next(q for q in P if q["pid"] == o["c1"]); att.append((p, {"input": o["input"], "block": o["block"], "hash": o["hash"]}, False, o))
    att.sort(key=lambda x: x[1]["block"])
    print("(1) our 8 C-1 buy attempts: the engine's minOut rebuilt from the chain against the minOut word of the real transaction")
    for p, t, filled, s in att:
        inp = t["input"]; stake = wd(inp, 5); mo = wd(inp, 6); dl = wd(inp, 7)
        cp, trig = engine_copy(p)
        k, ts_, cpt = trig
        mine = int(v4math.buy_out_int(int(cpt), LIQ, stake, FEE) * (1 - SLIP))
        B = t["block"]
        # the real pool at the top of our block (every swap of the blocks before ours, and of our own block before our index)
        my_idx = s.get("ti") if filled else s.get("txindex")
        st = None
        for x in p["sw"]:
            if x["cls"] == "ours": continue
            if x["bn"] < B or (x["bn"] == B and x["ti"] < my_idx): st = x
            else: break
        got = v4math.buy_out_int(st["sqrtP"], st["liq"], stake, st["fee"])
        real_tok = s["tok"] if filled else None
        print(f"   {utc(p['ts'])} {p['pid'][:10]} T +{ts_['off']} ({ts_['eth']:.4f} ETH, tx idx {ts_['ti']}) buy at T+{B - ts_['bn']} idx {my_idx} "
              f"{'FILLED' if filled else 'REVERTED'}: minOut on chain {mo} | rebuilt {mine} | {'EQUAL' if mo == mine else 'DIFF %+.2e' % (mine / mo - 1)}; "
              f"pool gives {got} = {got / mo - 1:+.2%} vs minOut" + (f"; real tokens {real_tok} ({'exact' if real_tok == got else '%+.1e' % (got / real_tok - 1)})" if filled else "")
              + f"; fire block ts - launch ts {dl - 3 - p['ts']} s (T at ~{ts_['off'] / 9.69:.1f} s)")
    # ---- how often a router call carries an amount the Swap log does not (none expected), and buys the feed cannot see
    c = collections.Counter()
    for p in P:
        for s in p["sw"]:
            a = seen(p, s)
            if s["buy"] and s["cls"] != "ours": c[a[0] if a else "none (value 0, not router)"] += 1
            if a and a[0] == "router" and a[1] != s["eth_wei"]: c["router amount != swap eth"] += 1
    print("\n(2) buys by what the feed shows:", dict(c))
