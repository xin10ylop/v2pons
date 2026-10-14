#!/usr/bin/env python3
"""base_relay_sim.py: a buy and a sell through the FlipRelay on one of the operator's Base pools, with nothing sent (deploy/relay_sim.py's
method on Base, as research/session_oct14/base2433/b07_exittest.py ran it). An eth_call with state overrides puts the relay's runtime code
(PoolManager = Base's, owner = a harness) at one address with ETH, and contracts/RoundTripHarness.sol at another as its owner; the harness
buys through the pool (the PoolKey carries the operator's hook), reads the balance, sells everything back and checks the accounting.
Prints the tokens the buy got against v4math's prediction from the pool's state at that block, the ETH the sell got back, and whether a
buy with minOut one above the real output is refused (TooLittleOut).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_relay_sim.py                          # the operator's latest pool
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_relay_sim.py <poolId> [eth] [--block N] # a given pool (ETH-paired, any hook)

The operator's latest pool: the newest Initialize with currency0 = ETH, fee BASE_FEE (5000), tick spacing BASE_TICK_SPACING (100), a hook
whose address flags are BASE_HOOK_FLAGS (0x80) and a token whose code hash is in BASE_TOKEN_CODEHASHES, searched back from the head
(--back N blocks, a day by default), with liquidity added. A pool still open is simulated at the head. A pulled pool (the operator pulls
about 4 minutes after the launch) is simulated at a past block after its add and before its pull (its add + 2, the block of our buy),
through Tenderly's public gateway, which keeps old state; the screen says so. [eth] is the stake (BASE_STAKE_ETH, 0.002 by default);
--block N simulates at block N (after the add, before the pull). Reads: logs from https://base-rpc.publicnode.com (its last ~10,000
blocks) and https://base.gateway.tenderly.co (older, 1,000 blocks a call); eth_call at a recent block from BASE_RPC_URL / BASE_READ_ALT_URL,
at an older one from Tenderly. The harness is compiled with solc 0.8.26 (py-solc-x downloads it once, about 10 MB). No key is read.

The module is also base_relay_deploy.py's check of a new relay (buy_through: a simulated buy through the deployed relay)."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "src"))
import base_wallet as BW
import relay_sim as RS
import v4math
from eth_utils import keccak

PM = (BW.setting("BASE_POOL_MANAGER", BW.PM) or BW.PM).lower()
RS.PM = PM                                                                               # relay_runtime() fills the immutables with Base's PoolManager
LOGS_URL = "https://base-rpc.publicnode.com"                                             # eth_getLogs over its last ~10,000 blocks, 5,000 a call here
ARCHIVE_URL = "https://base.gateway.tenderly.co"                                         # older logs (1,000 blocks a call); eth_call with overrides at old blocks
RECENT = 9000                                                                            # blocks LOGS_URL is asked for
DAY = 43200                                                                              # Base blocks in 24 h
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
ZERO32 = "0x" + "0" * 64
RELAY_AT = "0x" + "f1" * 20; HARNESS_AT = "0x" + "a1" * 20; CALLER = "0x" + "c0" * 20
SEL_RUN = keccak(text="run(address,(address,address,uint24,int24,address),uint256,uint256)").hex()[:8]
TOO_LITTLE = "e20a4c5d"; NOTHING_TO_SELL = "cb72d3db"
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16); A = lambda d, i: "0x" + d[2 + 64 * i + 24: 2 + 64 * (i + 1)]
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = RS.word
short = lambda x: x[:6] + "…" + x[-4:]


def post(url, m, p, tries=4, timeout=60):
    """one call with retries on a transport failure or a rate limit; a node's own error (a revert) raises BW.RpcError at once"""
    last = None
    for i in range(tries):
        try:
            return BW.post(url, m, p, timeout)
        except ConnectionError as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(last))


def head():
    return int(post(LOGS_URL, "eth_blockNumber", []), 16)


def chunk_logs(flt, a, b, hd):
    """the logs of flt in [a, b]: publicnode for recent blocks, else (or when it refuses) Tenderly 1,000 blocks at a time"""
    if a >= hd - RECENT:
        try:
            return post(LOGS_URL, "eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))], tries=2)
        except Exception:
            pass
    out = []
    for x in range(a, b + 1, 1000):
        out += post(ARCHIVE_URL, "eth_getLogs", [dict(flt, fromBlock=hex(x), toBlock=hex(min(b, x + 999)))])
    return out


def logs(flt, a, b, hd):
    out = []
    for x in range(a, b + 1, 5000):
        out += chunk_logs(flt, x, min(b, x + 4999), hd)
    return out


def logs_back(flt, hi, lo, hd):
    """chunks of logs from hi down to lo, the newest chunk first (each chunk oldest first)"""
    b = hi
    while b >= lo:
        size = 5000 if b - 5000 >= hd - RECENT else 1000
        a = max(lo, b - size + 1)
        yield chunk_logs(flt, a, b, hd)
        b = a - 1


def key_of(init):
    d = init["data"]
    return {"currency0": "0x" + init["topics"][2][-40:], "currency1": "0x" + init["topics"][3][-40:], "fee": W(d, 0),
            "tickSpacing": sgn(W(d, 1)), "hooks": A(d, 2)}


def code_hash(addr):
    code = BW.rpc("eth_getCode", [addr, "latest"])
    return "0x" + keccak(bytes.fromhex(code[2:])).hex() if code and len(code) > 2 else None


def line_filter():
    fee = int(BW.setting("BASE_FEE", "5000")); ts = int(BW.setting("BASE_TICK_SPACING", "100"))
    flags = int(BW.setting("BASE_HOOK_FLAGS", "0x80"), 0)
    hashes = {h.lower() if h.lower().startswith("0x") else "0x" + h.lower() for h in BW.url_list(BW.setting(
        "BASE_TOKEN_CODEHASHES", "0x63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb"))}
    return fee, ts, flags, hashes


def operator_inits(hd, back):
    """the operator's Initialize logs, newest first"""
    fee, ts, flags, hashes = line_filter()
    for chunk in logs_back({"address": PM, "topics": [T_INIT, None, ZERO32]}, hd, max(1, hd - back), hd):
        for l in reversed(chunk):
            k = key_of(l)
            if k["fee"] != fee or k["tickSpacing"] != ts:
                continue
            hk = int(k["hooks"], 16) & 0x3FFF
            if flags != -1 and hk != flags:
                continue
            if hashes and code_hash(k["currency1"]) not in hashes:
                continue
            yield l


def find_init(pid, hi, hd, back):
    for chunk in logs_back({"address": PM, "topics": [T_INIT, pid]}, hi, max(1, hi - back), hd):
        if chunk:
            return chunk[0]
    sys.exit(f"no Initialize of pool {pid} in the {back:,} blocks up to {hi} (--back N to look further)")


class Pool:
    """a pool's key and history: the blocks of its adds and pulls, and its state (sqrtP, tick, active liquidity) at any block"""

    def __init__(self, init, hd):
        self.init = init; self.key = key_of(init); self.pid = init["topics"][1]; self.L = int(init["blockNumber"], 16)
        self.ev = logs({"address": PM, "topics": [[T_SWAP, T_ML], self.pid]}, self.L, hd, hd)
        self.ev.sort(key=lambda e: (int(e["blockNumber"], 16), int(e["logIndex"], 16)))
        mls = [(int(e["blockNumber"], 16), sgn(W(e["data"], 2)), e) for e in self.ev if e["topics"][0] == T_ML]
        self.adds = [b for b, dl, _ in mls if dl > 0]; self.pulls = [b for b, dl, _ in mls if dl < 0]
        self.add_tx = next((e["transactionHash"] for b, dl, e in mls if dl > 0), None)

    def state(self, block):
        d = self.init["data"]; sqrt_p, tick, liq, swaps = W(d, 3), sgn(W(d, 4)), 0, 0
        for e in self.ev:
            if int(e["blockNumber"], 16) > block:
                break
            x = e["data"]
            if e["topics"][0] == T_ML:
                lo, hi, dl = sgn(W(x, 0)), sgn(W(x, 1)), sgn(W(x, 2))
                if lo <= tick < hi:
                    liq += dl
            else:
                sqrt_p, liq, tick, swaps = W(x, 2), W(x, 3), sgn(W(x, 4)), swaps + 1
        return sqrt_p, tick, liq, swaps

    def add_eth(self):
        try:
            t = post(ARCHIVE_URL, "eth_getTransactionByHash", [self.add_tx], tries=2)
            return int(t["value"], 16) / 1e18
        except Exception:
            return None

    def describe(self):
        k = self.key; off = lambda bs: ", ".join("+%d" % (b - self.L) for b in sorted(set(bs))) or "none"
        return (f"pool {self.pid[:14]}…: token {k['currency1']}, fee {k['fee'] / 1e4:g}%, tick spacing {k['tickSpacing']}, hook {k['hooks']} "
                f"(flags 0x{int(k['hooks'], 16) & 0x3FFF:x}); launched block {self.L}; liquidity added {off(self.adds)}, pulled {off(self.pulls)}")


def call_at(tx, block, ov, hd):
    """eth_call with overrides at block: a recent one from BASE_RPC_URL / BASE_READ_ALT_URL first, an older one from Tenderly first.
    Returns (result, host). A revert raises BW.RpcError (not asked elsewhere); a node that lacks the state is passed over."""
    urls = BW.rpc_urls() + [ARCHIVE_URL] if hd - block <= 60 else [ARCHIVE_URL] + BW.rpc_urls()
    last = None
    for u in urls:
        try:
            return post(u, "eth_call", [tx, hex(block), ov], tries=2), BW.host(u)
        except BW.RpcError as e:
            if "revert" in str(e).lower() or TOO_LITTLE in str(e) or NOTHING_TO_SELL in str(e):
                raise
            last = e
        except RuntimeError as e:
            last = e
    raise RuntimeError(f"no endpoint answered the eth_call at block {block}: {last}")


def simulate(pool, block, amount, hd):
    """the round trip through the harness at block; prints the result; True when the buy matched v4math and the accounting held"""
    k = pool.key
    if k["currency0"] != BW.ZERO:
        sys.exit("not an ETH-paired pool (currency0 is not ETH): the relay trades ETH pools only")
    sqrt_p, tick, liq, swaps = pool.state(block)
    print(f"the pool at block {block}: sqrtPriceX96 {sqrt_p}, tick {tick}, active liquidity {liq} ({swaps} swap(s) before)")
    if liq <= 0:
        sys.exit(f"no liquidity at block {block}: nothing to simulate")
    expect = v4math.buy_out_int(sqrt_p, liq, amount, k["fee"])
    harness = RS.compile_harness(); relay = RS.relay_runtime(HARNESS_AT)
    data = ("0x" + SEL_RUN + word(RELAY_AT) + word(k["currency0"]) + word(k["currency1"]) + word(k["fee"]) + word(k["tickSpacing"])
            + word(k["hooks"]) + word(amount))
    ov = {RELAY_AT: {"code": relay, "balance": hex(amount * 2)}, HARNESS_AT: {"code": harness}}
    tx = {"from": CALLER, "to": HARNESS_AT, "data": data + word(0), "gas": hex(5_000_000)}
    t0 = time.time()
    try:
        r, via = call_at(tx, block, ov, hd)
    except BW.RpcError as e:
        why = "the buy got no tokens (NothingToSell on the sell)" if NOTHING_TO_SELL in str(e) else str(e)[:300]
        print(f"the simulated round trip REVERTED: {why}"); return False
    tokens_out, held, eth_back, eth_after = (W(r, i) for i in range(4))
    print(f"eth_call in {1000 * (time.time() - t0):.0f} ms via {via}")
    if tokens_out == 0:
        print("the buy got no tokens at this block"); return False
    rel = (tokens_out - expect) / expect if expect else float("inf"); exact = abs(rel) < 1e-9
    print(f"buy  {amount / 1e18:.6f} ETH -> {tokens_out:.6g} tokens (v4math predicted {expect:.6g}: "
          f"{'exact' if tokens_out == expect else '%d raw unit(s) off, %+.1e relative' % (tokens_out - expect, rel)}: {'ok' if exact else 'MISMATCH'}); "
          f"the relay holds {held:.6g}")
    print(f"sell all -> {eth_back / 1e18:.6f} ETH back ({(eth_back - amount) / amount:+.2%} round trip at the pool's fee {k['fee'] / 1e4:g}% each way); "
          f"relay ETH after {eth_after / 1e18:.6f}, tokens left 0: accounting ok")
    ok_min = False
    try:
        call_at(dict(tx, data=data + word(tokens_out + 1)), block, ov, hd)
        print("a buy with minOut one above the real output WENT THROUGH: the relay does not enforce minOut; do not use it")
    except BW.RpcError as e:
        ok_min = TOO_LITTLE in str(e)
        print("a buy with minOut one above the real output is refused:", "TooLittleOut ok" if ok_min else "reverted, but not with TooLittleOut: " + str(e)[:200])
    return exact and ok_min


def latest_operator_pool(hd, back, want_open=False):
    """the operator's newest pool with liquidity added by the head (and not pulled, with want_open); None when none in the window"""
    for init in operator_inits(hd, back):
        p = Pool(init, hd)
        if not p.adds:
            print(f"(pool {p.pid[:14]}… launched at block {p.L} has no liquidity yet: the one before it)")
            continue
        if want_open and p.pulls:
            continue
        return p
    return None


def any_live_pool(hd):
    """the newest ETH-paired pool without a hook, initialised in the last ~9,000 blocks, with liquidity and a swap: a fallback for the
    deployment's check when the operator has no pool open"""
    seen = 0
    for chunk in logs_back({"address": PM, "topics": [T_INIT, None, ZERO32]}, hd, hd - RECENT + 10, hd):
        for l in reversed(chunk):
            if int(key_of(l)["hooks"], 16) != 0:
                continue
            seen += 1
            if seen > 40:
                return None
            p = Pool(l, hd)
            sqrt_p, tick, liq, swaps = p.state(hd)
            if liq > 0 and swaps and p.adds:
                return p
    return None


def buy_through(relay, owner, amount=10 ** 14):
    """base_relay_deploy.py's check: a buy through the DEPLOYED relay (eth_call from its owner, the relay's balance set by override) on
    the operator's open pool, else on any live ETH-paired pool, against v4math. True when it went through with the predicted tokens"""
    hd = head(); p = latest_operator_pool(hd, DAY, want_open=True); kind = "the operator's open pool"
    if p is None:
        p = any_live_pool(hd); kind = "a live ETH-paired pool without a hook (no operator pool is open: it pulls each about 4 minutes after its launch)"
    if p is None:
        print("no pool to simulate a buy on (no operator pool open, no recent hook-less ETH pool with swaps): run base_relay_sim.py later"); return None
    k = p.key; sqrt_p, tick, liq, swaps = p.state(hd)
    data = "0x5ed06f60" + word(k["currency0"]) + word(k["currency1"]) + word(k["fee"]) + word(k["tickSpacing"]) + word(k["hooks"]) + word(amount) + word(0) + word(0)
    try:
        r, via = call_at({"from": owner, "to": relay, "data": data, "gas": hex(3_000_000)}, hd, {relay: {"balance": hex(10 ** 16)}}, hd)
    except Exception as e:
        print(f"the simulated buy through the relay on {kind} ({p.pid[:14]}…) did not go through: {str(e)[:200]}"); return False
    got = int(r, 16); exp = v4math.buy_out_int(sqrt_p, liq, amount, k["fee"]); rel = (got - exp) / exp if exp else float("inf")
    ok = got > 0 and abs(rel) < 1e-9
    note = "ok" if ok else ("MISMATCH: do not use the relay" if kind.startswith("the operator") else
                            "the buy went through; this pool's liquidity is not the one range v4math assumes" if got > 0 else "NO TOKENS: look before using it")
    print(f"simulated buy through the relay on {kind}: pool {p.pid[:14]}… (token {k['currency1']}, fee {k['fee'] / 1e4:g}%, hook {short(k['hooks'])}) "
          f"at block {hd}: {amount / 1e18:g} ETH -> {got:.6g} tokens, v4math predicted {exp:.6g} ({rel:+.1e} relative: {note}) via {via}")
    return ok or (got > 0 and not kind.startswith("the operator"))


def main(argv):
    args, opts, i = [], {}, 0
    while i < len(argv):
        x = argv[i]
        if x in ("--block", "--back"):
            try:
                opts[x] = int(argv[i + 1]); i += 2; continue
            except (IndexError, ValueError):
                sys.exit(f"{x} takes a whole number (a block, or a count of blocks)")
        if x.startswith("--"):
            sys.exit(__doc__.split("\n\n")[1])
        args.append(x); i += 1
    back = opts.get("--back", DAY)
    pid = args[0].lower() if args and args[0].startswith("0x") else None
    if pid and len(pid) != 66:
        sys.exit("a pool id is 0x and 64 hex digits")
    rest = args[1:] if pid else args
    try:
        amount = int(float(rest[0] if rest else BW.setting("BASE_STAKE_ETH", "0.002")) * 1e18)
    except ValueError:
        sys.exit("the amount is in ETH, e.g. 0.002")
    if not 0 < amount <= 10 ** 18:
        sys.exit("the amount is in ETH, above 0 and at most 1")
    hd = head()
    if pid:
        p = Pool(find_init(pid, opts.get("--block", hd), hd, back), hd)
    else:
        p = latest_operator_pool(hd, back)
        if p is None:
            sys.exit(f"no operator pool with liquidity in the last {back:,} blocks (--back N to look further)")
        print("the operator's latest pool (fee %d, tick spacing %d, hook flags 0x%x, token code in BASE_TOKEN_CODEHASHES):" % line_filter()[:3])
    print(p.describe())
    if not p.adds:
        sys.exit("no liquidity was ever added to this pool: nothing to simulate")
    add, pull = p.adds[0], (p.pulls[0] if p.pulls else None)
    if "--block" in opts:
        blk = opts["--block"]
        if blk < add:
            sys.exit(f"block {blk} is before the liquidity (block {add}, +{add - p.L}): pick a block from {add}")
        if pull and blk >= pull:
            sys.exit(f"the pool was pulled at block {pull} (+{pull - p.L}): pick a block from {add} to {pull - 1}")
        if blk > hd:
            sys.exit(f"block {blk} is after the head {hd}")
        print(f"simulated at block {blk} (+{blk - p.L}){' (the pool is pulled now: the state of that block, through ' + BW.host(ARCHIVE_URL) + ')' if pull else ''}")
    elif pull:
        blk = min(add + 2, pull - 1)
        print(f"the pool was pulled at block {pull} (+{pull - p.L}): simulated at block {blk} (+{blk - p.L}), after the add and before the pull, "
              f"where our buy would land (Tenderly's state of that block; --block N for another)")
    else:
        blk = hd
        print(f"the pool is open: simulated at the head, block {blk} (+{blk - p.L})")
    eth = p.add_eth()
    if eth is not None:
        print(f"the add's transaction carried {eth:.6f} ETH (BASE_MIN_POOL_ETH {BW.setting('BASE_MIN_POOL_ETH', '1.0')}: "
              f"{'traded' if eth >= float(BW.setting('BASE_MIN_POOL_ETH', '1.0')) else 'a test pool the engine skips'})")
    ok = simulate(p, blk, amount, hd)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
