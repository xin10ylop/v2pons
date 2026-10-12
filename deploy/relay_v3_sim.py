#!/usr/bin/env python3
"""Run buys and sells through FlipRelayV3 on live Uniswap V3 pools without sending anything: eth_call with state overrides puts the
relay's runtime code (its owner filled in) at one address with an ETH balance, and a harness contract (RoundTripHarnessV3) at another
as its owner; the harness takes QuoterV2's quote, buys, reads the relay's balance, takes the sell's quote, sells everything and checks
the accounting, all on one block's state. Prints each leg against QuoterV2 and against the exact V3 swap math from the pool's slot0
and liquidity (one range), the round trip's loss, the gas of a buy transaction (eth_estimateGas with the same overrides) and about
that of a sell, then the failure paths, each of which must revert with its own error, and the owner's calls that must go through.

    python3 deploy/relay_v3_sim.py                       # from the factory's WETH pools of the last 24 h: the newest live pool of each
                                                         # line (p356, the self-buyer, the 836-byte crowd), the newest live one with WETH
                                                         # as token1, and the newest pulled one (a fill cut short)
    python3 deploy/relay_v3_sim.py --hours 8             # another window
    python3 deploy/relay_v3_sim.py 0xPOOL [0xPOOL ...]   # given WETH pools of the Uniswap V3 factory
    python3 deploy/relay_v3_sim.py --eth 0.005           # the buy's size (default 0.002 ETH)

A pool whose token refuses a transfer into the pool from an outside address (a sell lock: the relay could buy, never sell) is skipped
in the search and named; given by hand, it is reported as such. Exit status 1 if anything is not as expected, 2 if no live pool
was found to run a round trip on (nothing wrong, nothing proven).
"""
import argparse, json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay_sim
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); word = relay_sim.word; W = relay_sim.W
FACTORY = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
POOL_INIT_CODE_HASH = "e34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54"
NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"       # Uniswap V3's NonfungiblePositionManager
QUOTER = "0x33e885ed0ec9bf04ecfb19341582aadcb4c8a9e7"    # Uniswap's QuoterV2: the V3 deployer's nonce 6 (the factory is its nonce 2); factory() and WETH9() are the two above
RELAY_AT = "0x" + "f3" * 20; HARNESS_AT = "0x" + "a3" * 20; STRANGER = "0x" + "c0" * 20
P356_CODE = "89885b75"                                  # the 356-byte line's launcher code keccak (HANDOFF 16.18)
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
sel = lambda sig: keccak(text=sig).hex()[:8]
ERRORS = {sel(s): s for s in ("NotOwner()", "NotPool(address)", "Busy()", "TooLate(uint256,uint256)", "NoPool(address)", "Insufficient(uint256,uint256)",
                              "NothingToSell(address)", "TooLittleOut(uint256,uint256)", "Overpay(uint256,uint256)", "TransferFailed(address)")}
S_BUY, S_SELL, S_CB = sel("buy(address,uint24,uint256,uint256,uint256)"), sel("sell(address,uint24,uint256,uint256)"), sel("uniswapV3SwapCallback(int256,int256,bytes)")
S_WD, S_SWEEP = sel("withdraw(uint256)"), sel("sweep(address,uint256)")
S_RUN, S_BUY_ONLY = sel("run((address,address,address,address,uint24,uint256,uint256,uint256,uint256))"), sel("buyOnly(address,address,uint24,uint256,uint256,uint256)")
S_BUY_SWEEP = sel("buySweep(address,address,uint24,uint256,uint256,uint256)")
S_QUOTE = sel("quoteExactInputSingle((address,address,uint256,uint24,uint160))")
Q96 = 1 << 96; U256 = 1 << 256


# ---- the exact V3 swap math within one range (SqrtPriceMath; SwapMath.computeSwapStep for an exact input that stays in its range)
def _div_up(a, b): return -(-a // b)
def _next_sqrt_amount0_up(s, L, x):                    # token0 in: the price goes down
    n1 = L << 96; p = x * s
    if p < U256 and n1 + p < U256:
        return _div_up(n1 * s, n1 + p)
    return _div_up(n1, n1 // s + x)
def _next_sqrt_amount1_down(s, L, x):                  # token1 in: the price goes up
    return s + ((x << 96) // L if x < (1 << 160) else x * Q96 // L)
def v3_exact_in(s, L, amount, fee, zero_for_one):
    """(out, sqrtP after) of an exact-input swap of `amount` that stays in the current range"""
    if L == 0:
        return 0, s
    x = amount * (1_000_000 - fee) // 1_000_000
    if zero_for_one:
        s2 = _next_sqrt_amount0_up(s, L, x); return L * (s - s2) // Q96, s2
    s2 = _next_sqrt_amount1_down(s, L, x); return ((L << 96) * (s2 - s) // s2) // s, s2


# ---- RPC
def batch(method, plist, n=20):
    out = []
    for i in range(0, len(plist), n):
        body = json.dumps([{"jsonrpc": "2.0", "id": j, "method": method, "params": p} for j, p in enumerate(plist[i:i + n])]).encode()
        for k in range(6):
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(relay_sim.RPC, body, relay_sim.H), timeout=60))
                if isinstance(d, list): break
            except Exception:
                pass
            time.sleep(2 * (k + 1))
        else:
            raise RuntimeError(f"{method} batch failed")
        out += [x.get("result") for x in sorted(d, key=lambda x: x["id"])]
    return out


def decode_revert(d):
    if isinstance(d, str) and d[2:10] in ERRORS:
        sig = ERRORS[d[2:10]]; args = sig[sig.index("(") + 1:-1].split(",") if "()" not in sig else []
        vals = [("0x" + d[10 + 64 * i + 24:10 + 64 * (i + 1)]) if t == "address" else str(int(d[10 + 64 * i:10 + 64 * (i + 1)], 16)) for i, t in enumerate(args)]
        return sig[:sig.index("(")] + "(" + ", ".join(vals) + ")"
    if isinstance(d, str) and d[2:10] == "08c379a0":
        return "Error(" + bytes.fromhex(d[138:138 + 2 * int(d[74:138], 16)]).decode(errors="replace") + ")"
    return None


def call(to, data, block, frm=STRANGER, ov=None, gas=6_000_000):
    """(True, result) or (False, the revert: an error name with its arguments, a require string, or the RPC's message)"""
    try:
        return True, relay_sim.rpc("eth_call", [{"from": frm, "to": to, "data": data, "gas": hex(gas)}, block] + ([ov] if ov else []), tries=3)
    except RuntimeError as e:
        try:
            err = json.loads(str(e)); d = err.get("data") or ""
        except ValueError:
            return False, str(e)[:200]
        return False, decode_revert(d) or ((err.get("message") or "") + (" " + d if d else ""))


def estimate(to, data, block, frm, ov):
    try:
        return int(relay_sim.rpc("eth_estimateGas", [{"from": frm, "to": to, "data": data}, block, ov], tries=2), 16)
    except RuntimeError:
        return None


# ---- the code under test
def compile_harness():
    import solcx
    if "0.8.26" not in [str(v) for v in solcx.get_installed_solc_versions()]:
        print("installing solc 0.8.26 (once, about 10 MB)"); solcx.install_solc("0.8.26")
    src = open(os.path.join(ROOT, "contracts", "RoundTripHarnessV3.sol")).read()
    r = solcx.compile_standard({"language": "Solidity", "sources": {"H.sol": {"content": src}}, "settings": {"optimizer": {"enabled": True, "runs": 200}, "evmVersion": "cancun",
                                "outputSelection": {"*": {"RoundTripHarnessV3": ["evm.deployedBytecode.object"]}}}}, solc_version="0.8.26")
    return "0x" + r["contracts"]["H.sol"]["RoundTripHarnessV3"]["evm"]["deployedBytecode"]["object"]


def relay_v3_runtime(owner):
    """the artifact's runtime code with its one immutable (owner) filled in: what a deployment for `owner` puts on the chain"""
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelayV3.json"))); code = bytearray.fromhex(art["deployedBytecode"][2:])
    assert len(art["immutableReferences"]) == 1, art["immutableReferences"]
    for refs in art["immutableReferences"].values():
        for r in refs:
            code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(owner[2:])
    return "0x" + code.hex()


# ---- the pools
def pool_addr(token, fee):
    """Uniswap V3's PoolAddress.computeAddress for (WETH, token, fee)"""
    t0, t1 = sorted([token.lower(), WETH])
    salt = keccak(bytes.fromhex(t0[2:]).rjust(32, b"\0") + bytes.fromhex(t1[2:]).rjust(32, b"\0") + fee.to_bytes(32, "big"))
    return "0x" + keccak(b"\xff" + bytes.fromhex(FACTORY[2:]) + salt + bytes.fromhex(POOL_INIT_CODE_HASH))[12:].hex()


def pool_meta(pool, block="latest"):
    t0, t1, fee = (call(pool, "0x" + s, block)[1] for s in ("0dfe1681", "d21220a7", "ddca3f43"))
    return {"pool": pool.lower(), "token0": "0x" + t0[-40:], "token1": "0x" + t1[-40:], "fee": int(fee, 16)}


def token_of(p): return p["token1"] if p["token0"] == WETH else p["token0"]


def quote(token_in, token_out, amount, fee, block):
    ok, r = call(QUOTER, "0x" + S_QUOTE + word(token_in) + word(token_out) + word(amount) + word(fee) + word(0), block)
    return W(r, 0) if ok else 0


def liquidity(pool, block="latest"):
    ok, r = call(pool, "0x1a686502", block)
    return int(r, 16) if ok else 0


def sell_lock(p, block="latest"):
    """None, or the token's revert reason for a transfer of 0 into the pool from an outside address (a sell lock: buys go through, sells never)"""
    ok, r = call(token_of(p), "0xa9059cbb" + word(p["pool"]) + word(0), block)
    return None if ok else r


def family_of(tx):
    to = (tx.get("to") or "").lower(); inp = tx["input"]; n = (len(inp) - 2) // 2; v = int(tx["value"], 16)
    if to == NPM and inp[:10] == "0xac9650d8" and n == 836 and v == 0: return "crowd"
    if to == NPM and inp[:10] == "0x13ead562": return "selfbuyer"
    if to != NPM and inp[:10] == "0xd27d1e00" and n == 356: return "p356"
    return f"other {to[:10]} {inp[:10]} {n} B"


def recent_pools(hours):
    """the factory's WETH pools created in the last `hours`, oldest first, each with its launch call's family; and the blocks per second"""
    head = int(relay_sim.rpc("eth_blockNumber", []), 16); t_head = int(relay_sim.rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    t_old = int(relay_sim.rpc("eth_getBlockByNumber", [hex(head - 20000), False])["timestamp"], 16); bps = 20000 / max(1, t_head - t_old)
    start = head - int(hours * 3600 * bps); ls = []
    for a in range(start, head + 1, 100_000):
        ls += relay_sim.rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(a + 99_999, head)), "address": FACTORY, "topics": [T_PC]}])
    ls = [l for l in ls if WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
    txs = batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in ls])
    recs = [{"pool": "0x" + l["data"][-40:], "token0": "0x" + l["topics"][1][-40:], "token1": "0x" + l["topics"][2][-40:], "fee": int(l["topics"][3], 16),
             "block": int(l["blockNumber"], 16), "family": family_of(t), "launcher": (t.get("to") or "").lower()} for l, t in zip(ls, txs) if t]
    return recs, head, bps


def find_pools(hours, amount):
    """the newest live WETH pool of each line, the newest live one with WETH as token1 and the newest pulled one, among the factory's
    pools of the last `hours`; sell-locked tokens skipped and named"""
    recs, head, bps = recent_pools(hours)
    count = lambda f: sum(f(r["family"]) for r in recs)
    print(f"head {head}, {bps:.2f} blocks/s; the factory's WETH pools of the last {hours:g} h: {len(recs)}: p356 {count(lambda f: f == 'p356')}, "
          f"selfbuyer {count(lambda f: f == 'selfbuyer')}, crowd {count(lambda f: f == 'crowd')}; d27d1e00 calls of another length {count(lambda f: 'd27d1e00' in f)}; "
          f"other shapes {count(lambda f: f.startswith('other') and 'd27d1e00' not in f)}")
    picks = []; skipped = []
    for want in ("p356", "selfbuyer", "crowd", "weth-token1", "pulled"):
        cands = [r for r in reversed(recs) if (r["token1"] == WETH if want == "weth-token1" else True if want == "pulled" else r["family"] == want)]
        for r in cands[:40]:
            L = liquidity(r["pool"]); q = quote(WETH, token_of(r), amount, r["fee"], "latest")
            if (L or q) if want == "pulled" else not (L and q):
                continue
            if want == "pulled" and len(relay_sim.rpc("eth_getCode", [token_of(r), "latest"])) <= 2:
                continue
            lock = sell_lock(r) if want != "pulled" else None
            if lock:
                print(f"  {want}: pool {r['pool']} (launched block {r['block']}) skipped: its token refuses a transfer into the pool from an outside "
                      f"address, {lock}: a sell lock (the relay, as any outsider, could buy and never sell)")
                skipped.append((want, r, lock)); continue
            if r["family"] == "p356":
                r["launcher_code"] = keccak(bytes.fromhex(relay_sim.rpc("eth_getCode", [r["launcher"], "latest"])[2:])).hex()[:8]
            picks.append(dict(r, line=want)); break
        else:
            print(f"  {want}: none among the {len(cands)} of the window" + (" (try --hours 48)" if not cands else ""))
    return picks, skipped, bps


# ---- the tests
def round_trip(p, amount, block, ts, ov):
    tok = token_of(p); weth0 = p["token0"] == WETH; fee = p["fee"]
    data = "0x" + S_RUN + "".join(word(x) for x in (RELAY_AT, QUOTER, p["pool"], tok, fee, amount, 0, 0, ts + 600))
    ok, r = call(HARNESS_AT, data, block, ov=ov, gas=30_000_000)
    if not ok:
        return {"revert": r}
    v = [W(r, i) for i in range(15)]
    buy_math, s_after = v3_exact_in(v[0], v[1], amount, fee, weth0)
    sell_math, _ = v3_exact_in(v[6], v[7], v[5], fee, not weth0)
    rel = lambda got, exp: "exact" if got == exp else (f"off by {(got - exp) / exp:+.2e}" if exp else "none")
    loss = (amount - v[10]) / amount; fee2 = 1 - (1 - fee / 1e6) ** 2
    # the gas of the buy as a transaction (from the owner, on this state); the sell's estimate on this state would price another swap (the
    # buy is not in it), so the sell is its gas inside the harness plus the buy's transaction overhead (the estimate less the buy's inner gas)
    g_buy = estimate(RELAY_AT, "0x" + S_BUY + word(tok) + word(fee) + word(amount) + word(0) + word(ts + 600), block, HARNESS_AT, {RELAY_AT: ov[RELAY_AT]})
    g_sell = v[13] + g_buy - v[12] if g_buy else None
    print(f"  buy  {amount / 1e18:g} ETH -> {v[4]} tokens; QuoterV2 {v[2]} ({rel(v[4], v[2])}, {v[3]} initialized ticks crossed); "
          f"the one-range math from slot0/liquidity {buy_math} ({rel(v[4], buy_math)}); sqrtP after the buy {'= the math' if v[6] == s_after else 'differs from the one-range math'}")
    print(f"  sell all {v[5]} -> {v[10]} wei; QuoterV2 {v[8]} ({rel(v[10], v[8])}, {v[9]} ticks crossed); the one-range math {sell_math} ({rel(v[10], sell_math)})")
    print(f"  round trip -{loss:.4%} (two fees of {fee / 1e4:g}%: -{fee2:.4%}; the rest {fee2 - loss:+.5%}); the price ends at {v[14] / v[0]:.8f} of its start; "
          f"ETH accounting, no token and no WETH left in the relay: ok")
    print(f"  gas: buy {v[12]}, sell {v[13]} inside the harness; as transactions: buy {g_buy} (eth_estimateGas), sell about {g_sell}")
    return {"out": v[4], "quote": v[2], "math": buy_math, "eth_back": v[10], "sell_quote": v[8], "sell_math": sell_math, "loss": loss, "fee2": fee2,
            "gas_buy": g_buy or v[12], "gas_sell": g_sell or v[13], "ticks": (v[3], v[9])}


def failure_paths(p, amount, block, ts, ov, rt):
    tok = token_of(p); fee = p["fee"]; pool = p["pool"]
    buy = lambda amt, mn, dl, f=fee: "0x" + S_BUY + word(tok) + word(f) + word(amt) + word(mn) + word(dl)
    sell = lambda mn, dl: "0x" + S_SELL + word(tok) + word(fee) + word(mn) + word(dl)
    cb = lambda owed, named=WETH: "0x" + S_CB + word(owed) + word(0) + word(0x60) + word(32) + word(named)
    direct = {RELAY_AT: ov[RELAY_AT]}                                                        # the owner (HARNESS_AT) as a plain address
    slot = lambda i: "0x" + "%064x" % i
    busy = {RELAY_AT: dict(ov[RELAY_AT], stateDiff={slot(0): "0x" + word(pool)})}             # slot 0 (the swap in progress) set to the pool
    swap_buy = {RELAY_AT: dict(ov[RELAY_AT], stateDiff={slot(0): "0x" + word(pool), slot(1): "0x" + word(WETH), slot(2): "0x" + word(amount)})}  # a buy's record
    sweep = lambda t, amt: "0x" + S_SWEEP + word(t) + word(amt)
    bal = int(ov[RELAY_AT]["balance"], 16)
    no_fee = next(f for f in (500, 3000, 10000, 100) if f != fee and len(relay_sim.rpc("eth_getCode", [pool_addr(tok, f), "latest"])) <= 2)
    run_sell_min = "0x" + S_RUN + "".join(word(x) for x in (RELAY_AT, QUOTER, pool, tok, fee, amount, 0, rt["eth_back"] + 1, ts + 600))
    checks = [
        ("a stranger's buy", STRANGER, RELAY_AT, buy(amount, 0, ts + 600), direct, "NotOwner()"),
        ("a stranger's sell", STRANGER, RELAY_AT, sell(0, ts + 600), direct, "NotOwner()"),
        ("a stranger's withdraw(0)", STRANGER, RELAY_AT, "0x" + S_WD + word(0), direct, "NotOwner()"),
        ("a stranger's sweep(WETH, 0)", STRANGER, RELAY_AT, sweep(WETH, 0), direct, "NotOwner()"),
        ("the callback called by a stranger", STRANGER, RELAY_AT, cb(amount), direct, f"NotPool({STRANGER})"),
        ("the callback called by the pool itself, no swap in progress", pool, RELAY_AT, cb(amount), direct, f"NotPool({pool})"),
        ("the callback called by a stranger during a swap (slots set)", STRANGER, RELAY_AT, cb(amount), swap_buy, f"NotPool({STRANGER})"),
        ("the pool during a buy asking 1 wei over the recorded maximum", pool, RELAY_AT, cb(amount + 1), swap_buy, f"Overpay({amount + 1}, {amount})"),
        ("the pool during a buy, owed within the maximum, data naming the token: pays the recorded WETH (none here)", pool, RELAY_AT, cb(amount, tok),
         swap_buy, f"TransferFailed({WETH})"),
        ("the owner's buy during a swap (re-entry: slot set)", HARNESS_AT, RELAY_AT, buy(amount, 0, ts + 600), busy, "Busy()"),
        ("the owner's sell with nothing to sell", HARNESS_AT, RELAY_AT, sell(0, ts + 600), direct, f"NothingToSell({tok})"),
        ("the owner's buy past its deadline (the block's second - 1)", HARNESS_AT, RELAY_AT, buy(amount, 0, ts - 1), direct, f"TooLate({ts}, {ts - 1})"),
        ("the owner's buy for minOut one above its output", HARNESS_AT, RELAY_AT, buy(amount, rt["out"] + 1, ts + 600), direct, f"TooLittleOut({rt['out']}, {rt['out'] + 1})"),
        ("the owner's sell for minOut one above its output", STRANGER, HARNESS_AT, run_sell_min, ov, f"TooLittleOut({rt['eth_back']}, {rt['eth_back'] + 1})"),
        (f"the owner's buy on a pool that does not exist (fee {no_fee})", HARNESS_AT, RELAY_AT, buy(amount, 0, ts + 600, no_fee), direct, f"NoPool({pool_addr(tok, no_fee)})"),
        ("the owner's buy above the relay's ETH", HARNESS_AT, RELAY_AT, buy(bal + 1, 0, ts + 600), direct, f"Insufficient({bal}, {bal + 1})"),
        ("the owner's sweep of 1 wei of WETH with none there", HARNESS_AT, RELAY_AT, sweep(WETH, 1), direct, f"TransferFailed({WETH})"),
    ]
    bad = 0
    for name, frm, to, data, o, want in checks:
        ok, r = call(to, data, block, frm=frm, ov=o)
        good = not ok and r.lower() == want.lower()
        bad += not good
        print(f"  {'ok ' if good else 'BAD'} {name}: {'went through' if ok else r}{'' if good else f' (expected {want})'}")
    passes = [("the owner's buy with its deadline at the block's second", buy(amount, rt["out"], ts)),
              ("the owner's withdraw(0)", "0x" + S_WD + word(0)),
              ("the owner's sweep(WETH, 0) (nothing there)", sweep(WETH, 0))]
    for name, data in passes:
        ok, r = call(RELAY_AT, data, block, frm=HARNESS_AT, ov=direct)
        good = ok and (data[2:10] != S_BUY or W(r, 0) == rt["out"])
        bad += not good
        print(f"  {'ok ' if good else 'BAD'} {name}: {('goes through' + (f', {W(r, 0)} tokens' if data[2:10] == S_BUY else '')) if ok else 'REVERTED ' + r}")
    part = rt["out"] // 3                                                                     # a buy, then sweep(token, a third), then sweep(token, 0)
    ok, r = call(HARNESS_AT, "0x" + S_BUY_SWEEP + "".join(word(x) for x in (RELAY_AT, tok, fee, amount, ts + 600, part)), block, ov=ov, gas=30_000_000)
    v = [W(r, i) for i in range(5)] if ok else None
    good = bool(v) and v[1] == v[0] - part and v[2] == part and v[3] == 0 and v[4] == v[0]
    bad += not good
    print(f"  {'ok ' if good else 'BAD'} the owner's sweep(token, a third of the buy), then sweep(token, 0): "
          + (f"the relay holds {v[1]} then {v[3]}, the owner got {v[2]} then {v[4]} of {v[0]}" if v else r))
    return bad


def cut_short(p, amount, block, ts, ov):
    """a buy on a pool with no liquidity left: the swap walks to the price limit, takes nothing; minOut 0 gives 0 tokens and the WETH back as ETH"""
    tok = token_of(p); bad = 0
    for mn in (0, 1):
        data = "0x" + S_BUY_ONLY + "".join(word(x) for x in (RELAY_AT, tok, p["fee"], amount, mn, ts + 600))
        ok, r = call(HARNESS_AT, data, block, ov=ov, gas=100_000_000)
        if mn == 0:
            v = [W(r, i) for i in range(5)] if ok else None
            good = bool(v) and v[0] == 0 and v[1] == v[2] and v[3] == 0
            print(f"  {'ok ' if good else 'BAD'} a buy with minOut 0: " + (f"{v[0]} tokens, the relay's ETH {v[1]} before and {v[2]} after, WETH left {v[3]}; "
                  f"gas {v[4]} (the swap walks every empty tick word to the price limit" + ("; a transaction with a 400k limit runs out of gas and reverts)" if v[4] > 400_000
                  else ": it fits in a 400k limit)") if v else r))
        else:
            good = not ok and r == "TooLittleOut(0, 1)"
            print(f"  {'ok ' if good else 'BAD'} a buy with minOut 1: {'went through' if ok else r}")
        bad += not good
    return bad


def main():
    ap = argparse.ArgumentParser(description="FlipRelayV3 on live Uniswap V3 pools, by eth_call only (nothing is sent)")
    ap.add_argument("pools", nargs="*"); ap.add_argument("--eth", type=float, default=0.002); ap.add_argument("--hours", type=float, default=24.0)
    a = ap.parse_args(); amount = int(a.eth * 1e18)
    harness = compile_harness(); relay = relay_v3_runtime(HARNESS_AT)
    if a.pools:
        picks = []; skipped = []; bps = 9.7
        for x in a.pools:
            m = pool_meta(x)
            if WETH not in (m["token0"], m["token1"]) or pool_addr(token_of(m), m["fee"]) != m["pool"]:
                sys.exit(f"{x} is not a WETH pool of the Uniswap V3 factory")
            picks.append(dict(m, line="given", family="given", block=None, pulled=not liquidity(x) and not quote(WETH, token_of(m), amount, m["fee"], "latest")))
    else:
        picks, skipped, bps = find_pools(a.hours, amount)
    ov = {RELAY_AT: {"code": relay, "balance": hex(amount * 5)}, HARNESS_AT: {"code": harness}}
    total_bad = 0; results = []
    for p in picks:
        blk = int(relay_sim.rpc("eth_blockNumber", []), 16) - 2; block = hex(blk)
        ts = int(relay_sim.rpc("eth_getBlockByNumber", [block, False])["timestamp"], 16)
        age = f", launched block {p['block']} ({(blk - p['block']) / bps / 3600:.1f} h ago)" if p.get("block") else ""
        code = p.get("launcher_code")
        extra = f", launcher code {code}: {'the line' if code == P356_CODE else 'NOT the line'}" if code else ""
        print(f"\n[{p['line']}] pool {p['pool']} ({p['family']}{extra}): token {token_of(p)}, WETH as token{0 if p['token0'] == WETH else 1}, "
              f"fee {p['fee'] / 1e4:g}%{age}; the state of block {blk}")
        if p["line"] == "pulled" or p.get("pulled"):
            print(f"  liquidity {liquidity(p['pool'], block)}: a pulled pool")
            bad = cut_short(p, amount, block, ts, ov); total_bad += bad; results.append((p, None, bad)); continue
        rt = round_trip(p, amount, block, ts, ov)
        if "revert" in rt:
            lock = sell_lock(p, block)
            ok, r = call(RELAY_AT, "0x" + S_BUY + word(token_of(p)) + word(p["fee"]) + word(amount) + word(0) + word(ts + 600), block, frm=HARNESS_AT, ov={RELAY_AT: ov[RELAY_AT]})
            q = quote(WETH, token_of(p), amount, p["fee"], block)
            print(f"  the round trip reverted: {rt['revert']}; the buy alone: {W(r, 0) if ok else r} tokens (QuoterV2 {q})")
            if lock and ok and W(r, 0) == q and rt["revert"].startswith("TransferFailed"):
                print(f"  the token refuses a transfer into its pool from an outside address ({lock}): a sell lock; the relay is not at fault, the pool is not tradable")
                skipped.append((p["line"], p, lock))
            else:
                total_bad += 1
            continue
        bad = failure_paths(p, amount, block, ts, ov, rt); total_bad += bad
        results.append((p, rt, bad))
    print("\nsummary:")
    for p, rt, bad in results:
        head = f"  {p['line']:<11} {p['pool']} WETH token{0 if p['token0'] == WETH else 1} fee {p['fee']:>5}: "
        if rt is None:
            print(head + f"pulled: the cut-short buy {'ok' if not bad else 'BAD'}"); continue
        print(head + f"buy {'= QuoterV2' if rt['out'] == rt['quote'] else '!= QuoterV2'} ({'= one-range math' if rt['out'] == rt['math'] else 'one-range math off'}); "
              f"sell {'= QuoterV2' if rt['eth_back'] == rt['sell_quote'] else '!= QuoterV2'}; round trip -{rt['loss']:.4%} (two fees -{rt['fee2']:.4%}); "
              f"gas {rt['gas_buy']}/{rt['gas_sell']}; failure paths {'all ok' if not bad else f'{bad} BAD'}")
    for line, p, lock in skipped:
        print(f"  {line:<11} {p['pool']} sell-locked token ({lock}): skipped")
    if total_bad:
        print("SOMETHING IS NOT AS EXPECTED: do not deploy this build"); sys.exit(1)
    if not any(rt for _, rt, _ in results):
        print("no live pool found: no round trip was run (what did run is as expected); try --hours 48 or give a live pool"); sys.exit(2)
    print("all as expected")


if __name__ == "__main__":
    main()
