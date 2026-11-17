"""The fee-0 engine (src/fee0_engine.py) on synthetic PoolManager logs: a family launch (Initialize + the launch's liquidity + its own buys
in the launch block), the crowd's buys and sells after it, our relay's own swaps. The RPC (every read), the sequencer (every send) and the
key are stubbed; nothing reaches a network. Prices move by v4math, the engine's own pool math, so each case checks the decision (fire,
skip, exit and why) and the booked return against a return computed here. Each case prints "ok <name>"; the count at the end.
Plain script: python3 tests/test_fee0_engine.py"""
import os, sys, json, time, tempfile, concurrent.futures
import rlp
from eth_account import Account
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TMP = tempfile.mkdtemp(prefix="fee0_engine_test_")
LAUNCHER_CODE = "0x6080604052" + "11" * 60
for k in ("DRY_RUN", "WALLET", "RELAY", "PRIVATE_KEY", "REPLAY_FROM", "MAX_POSITIONS"):
    os.environ.pop(k, None)
os.environ.update({"LOG_PATH": os.path.join(TMP, "fee0.jsonl"), "HALT_FILE": os.path.join(TMP, "FEE0_HALTED"), "STAKE_ETH": "0.01", "ETH_USD": "3000",
                   "LAUNCHER_CODE_HASH": keccak(bytes.fromhex(LAUNCHER_CODE[2:])).hex(), "LAND_BLOCKS": "4", "STATUS_EVERY_S": "100000"})
sys.path.insert(0, os.path.join(ROOT, "src"))
import fee0_engine as E
import v4math

KEY = Account.create(); WALLET = KEY.address.lower(); RELAY = "0x" + "f1" * 20
PID = "0x" + "ab" * 32; TOKEN = "0x" + "cd" * 20; LAUNCH_TX = "0x" + "01" * 32; LAUNCHER = "0x" + "77" * 20; CROWD = "0x" + "88" * 20
L0 = 50_000 * 10 ** 18; SP0 = E.FAM_SQRT_P; LB = 1000                      # the pool's liquidity, launch price, launch block
w = lambda x: "%064x" % (x % (1 << 256))
TESTS = []; SEQ = [0]; PID2 = "0x" + "ac" * 32


def test(fn):
    TESTS.append(fn); return fn


class Chain:
    """the stubbed RPC: launch tx and launcher code, the exit test's eth_call, receipts, balances"""
    def __init__(self):
        self.exit_ok = True; self.receipts = {}; self.calls = []; self.token_bal = 0

    def rpc(self, method, params, url=None, tries=4, timeout=10):
        self.calls.append(method)
        if method == "eth_getTransactionByHash":
            return {"to": LAUNCHER, "input": "0x" + E.LAUNCH_SELECTOR + "00" * 64, "value": hex(5 * 10 ** 18), "from": "0x" + "99" * 20}
        if method == "eth_getCode":
            return LAUNCHER_CODE
        if method == "eth_call":
            if params[0]["to"] == E.HARNESS_AT:
                if not self.exit_ok:
                    raise RuntimeError('eth_call: {"code": 3, "message": "execution reverted"}')
                amt = int(params[0]["data"][2 + 8 + 64 * 6: 2 + 8 + 64 * 7], 16)
                return "0x" + w(10 ** 20) + w(10 ** 20) + w(amt) + w(amt)
            if params[0]["data"].startswith("0x70a08231"):
                return "0x" + w(self.token_bal)
        if method == "eth_getTransactionReceipt":
            return self.receipts.get(params[0])
        if method == "eth_getTransactionCount":
            return hex(7)
        if method == "eth_gasPrice":
            return hex(10 ** 7)
        raise RuntimeError(f"unstubbed {method}")


class Sent:
    def __init__(self):
        self.txs = []

    def send(self, raw):
        f = rlp.decode(raw)
        self.txs.append({"nonce": int.from_bytes(f[0], "big"), "to": "0x" + f[3].hex(), "data": f[5].hex(), "hash": "0x" + keccak(raw).hex()})
        return True, self.txs[-1]["hash"]


def log_init(pid=PID, fee=0, ts=60, hooks=0, sp=SP0, blk=LB):
    return {"blockNumber": hex(blk), "logIndex": hex(int(pid[2:6], 16)), "transactionHash": LAUNCH_TX, "topics": [E.T_INIT, pid, "0x" + w(0), "0x" + w(int(TOKEN, 16))],
            "data": "0x" + w(fee) + w(ts) + w(hooks) + w(sp) + w(0)}


def log_ml(delta, blk=LB, lo=-887220, hi=887220, pid=PID, i=1):     # a full-range position (tick 0 inside it)
    return {"blockNumber": hex(blk), "logIndex": hex(i), "transactionHash": LAUNCH_TX, "topics": [E.T_ML, pid, "0x" + w(0)], "data": "0x" + w(lo) + w(hi) + w(delta) + w(0)}


class Pool:
    """the pool's price, moved by v4math: buy(eth) and sell(tokens) return a Swap log"""
    def __init__(self):
        self.sp = SP0; self.n = 0

    def buy(self, eth, blk, sender=CROWD, pid=PID):
        tok = v4math.buy_out_int(self.sp, L0, eth, 0); self.sp = int(v4math.sqrt_after_buy(self.sp, L0, eth)); return self._log(-eth, tok, blk, sender, pid)

    def sell(self, tok, blk, sender=CROWD, pid=PID):
        eth = v4math.sell_out_int(self.sp, L0, tok, 0)
        self.sp = int(v4math.sqrt_after_buy(self.sp, L0, -eth)) if False else self._sp_after_sell(tok); return self._log(eth, -tok, blk, sender, pid)

    def _sp_after_sell(self, tok):
        # token in: 1/sqrtP falls by tok/L (currency1 in moves sqrtP up) -- sqrtP' = sqrtP + tok * 2^96 / L
        return self.sp + tok * (1 << 96) // L0

    def _log(self, a0, a1, blk, sender, pid):
        self.n += 1; SEQ[0] += 1                                                    # every synthetic log its own (tx, logIndex)
        return {"blockNumber": hex(blk), "logIndex": hex(10 + self.n), "transactionHash": "0x" + w(SEQ[0] + 1000), "topics": [E.T_SWAP, pid, "0x" + w(int(sender, 16))],
                "data": "0x" + w(a0) + w(a1) + w(self.sp) + w(L0) + w(0) + w(0)}


def fresh(dry=True, **kw):
    for f in (E.LOG_PATH, E.HALT_FILE):
        if os.path.exists(f):
            os.remove(f)
    E.DRY_RUN = dry; E.MAX_POSITIONS = 1; E.REPLAY_FROM = 0; E.WALLET = WALLET; E.RELAY = RELAY; E.MAX_TRADES_PER_DAY = 40; E.DAILY_STOP_USD = 10
    for k, v in kw.items():
        setattr(E, k, v)
    c = Chain(); E.rpc = c.rpc
    e = E.Engine(); e.gas_price = 3 * 10 ** 7
    if not dry:
        e.signer = KEY; e.sender = Sent(); e.nonce = 7
    return e, c


def drain(e):
    e.workers.shutdown(wait=True); e.workers = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def at(e, blk, logs=()):
    """the chain's head reaches blk with these logs; the engine's poll"""
    e.head = blk; e.ingest(list(logs)); e.tick(); e.maintain(); drain(e)


def events(name=None):
    if not os.path.exists(E.LOG_PATH):
        return []
    ev = [json.loads(l) for l in open(E.LOG_PATH)]
    return [x for x in ev if name is None or x["ev"] == name]


def launch(e, pool):
    """the launch block: Initialize, the liquidity, the launcher's own buy; then the exit test (a poll two blocks on)"""
    at(e, LB, [log_init(), log_ml(L0), pool.buy(5 * 10 ** 18, LB, sender="0x" + "20" * 20)])
    at(e, LB + 2)
    assert E.Engine is not None and e.pools[PID]["launcher"] is True and e.pools[PID]["check"] is True, e.pools[PID]


@test
def arms_only_the_family():
    e, c = fresh(); pool = Pool()
    at(e, LB, [log_init(pid="0x" + "01" * 32, fee=3000), log_init(pid="0x" + "02" * 32, hooks=1), log_init(pid="0x" + "03" * 32, sp=SP0 + 1),
               log_init(pid="0x" + "04" * 32, ts=200), log_init()])
    assert list(e.pools) == [PID], list(e.pools)


@test
def launch_block_buy_is_no_trigger():
    e, c = fresh(); pool = Pool(); launch(e, pool)
    assert not events("trigger") and e.pools[PID]["status"] == "armed"


@test
def dry_take_profit():
    e, c = fresh(); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])                     # the crowd's first buy: 0.03 ETH
    f = events("would_fire")[0]; assert f["land_block"] == LB + 304, f
    at(e, LB + 303)
    sp_in = pool.sp; q = v4math.buy_out_int(sp_in, L0, E.STAKE_WEI, 0)
    blk = LB + 304
    while not events("exit"):
        blk += 5; at(e, blk, [pool.buy(2 * 10 ** 17, blk)])
        assert blk < LB + 2000
    x = events("exit")[0]; assert x["why"].startswith("take profit"), x
    at(e, x["sell_land"])
    s = events("settled")[0]
    sp2 = int(v4math.sqrt_after_buy(pool.sp, L0, E.STAKE_WEI)); want = (v4math.sell_out_int(sp2, L0, q, 0) - E.STAKE_WEI - E.DRY_GAS_WEI) / E.STAKE_WEI
    assert abs(s["ret"] - want) < 1e-4 and s["ret"] >= 0.08, (s, want)
    assert e.trades == 1 and not e.pos


@test
def dry_stop_loss():
    e, c = fresh(); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)]); at(e, LB + 303)
    q = v4math.buy_out_int(pool.sp, L0, E.STAKE_WEI, 0)
    blk = LB + 310; at(e, blk, [pool.sell(q * 40, blk)])                       # a crowd sell much bigger than our tokens
    x = events("exit")[0]; assert x["why"].startswith("stop loss"), x
    at(e, x["sell_land"]); s = events("settled")[0]; assert s["ret"] < -0.05, s


@test
def dry_cap():
    e, c = fresh(); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)]); at(e, LB + 303)
    at(e, LB + 304 + E.HOLD_BLOCKS)
    x = events("exit")[0]; assert x["why"].startswith("the cap"), x


@test
def exit_test_failure_refuses_the_pool():
    e, c = fresh(); pool = Pool(); c.exit_ok = False
    at(e, LB, [log_init(), log_ml(L0), pool.buy(5 * 10 ** 18, LB)]); at(e, LB + 2)
    assert e.pools[PID]["status"] == "refused" and e.pools[PID]["check"] is False
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    assert not events("would_fire") and not events("trigger")


@test
def stale_exit_test_skips():
    e, c = fresh(); pool = Pool(); launch(e, pool)
    e.pools[PID]["check_at"] = LB - E.CHECK_MAX_AGE - 5; e.pools[PID]["checking"] = True      # an old verdict, no new one running
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    s = events("skip"); assert s and s[0]["why"].startswith("no recent exit test"), s


@test
def wrong_launcher_code_refuses():
    e, c = fresh(); pool = Pool()
    c.rpc_code = c.rpc
    E.rpc = lambda m, p, **k: "0x6080" if m == "eth_getCode" else c.rpc(m, p, **k)
    at(e, LB, [log_init(), log_ml(L0), pool.buy(5 * 10 ** 18, LB)])
    assert e.pools[PID]["launcher"] is False and e.pools[PID]["status"] == "refused"


@test
def live_round_trip():
    e, c = fresh(dry=False); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    b = e.sender.txs[0]
    assert b["to"] == RELAY and b["nonce"] == 7 and b["data"][:8] == E.SEL_BUY, b
    words = [int(b["data"][8 + 64 * i: 8 + 64 * (i + 1)], 16) for i in range(8)]
    assert words[0] == 0 and words[1] == int(TOKEN, 16) and words[2] == 0 and words[3] == 60 and words[4] == 0 and words[5] == E.STAKE_WEI, words
    exp = v4math.buy_out_int(pool.sp, L0, E.STAKE_WEI, 0); assert words[6] == int(exp * (1 - E.BUY_SLIP)), (words[6], exp)
    our = pool.buy(E.STAKE_WEI, LB + 302, sender=RELAY); q = -E.sgn(int(our["data"][2:66], 16)) * 0 + E.sgn(int(our["data"][66:130], 16))
    at(e, LB + 302, [our])
    assert e.pos[PID]["state"] == "open" and e.pos[PID]["tokens"] == q
    blk = LB + 302
    while len(e.sender.txs) < 2:
        blk += 5; at(e, blk, [pool.buy(2 * 10 ** 17, blk)])
    s = e.sender.txs[1]; assert s["data"][:8] == E.SEL_SELL and s["nonce"] == 8, s
    back = pool.sell(q, blk + 2, sender=RELAY); back["transactionHash"] = s["hash"]; eth = E.sgn(int(back["data"][2:66], 16))
    c.receipts = {b["hash"]: {"gasUsed": hex(100000), "effectiveGasPrice": hex(10 ** 7)}, s["hash"]: {"gasUsed": hex(100000), "effectiveGasPrice": hex(10 ** 7)}}
    at(e, blk + 2, [back])
    st = events("settled")[0]; want = (eth - E.STAKE_WEI - 2 * 10 ** 12) / E.STAKE_WEI
    assert abs(st["ret"] - want) < 1e-4 and st["dry"] is False and st["ret"] > 0.07, (st, want)
    assert not e.pos and not os.path.exists(E.HALT_FILE)


@test
def live_short_sell_halts():
    e, c = fresh(dry=False); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    our = pool.buy(E.STAKE_WEI, LB + 302, sender=RELAY); at(e, LB + 302, [our])
    blk = LB + 302
    while len(e.sender.txs) < 2:
        blk += 5; at(e, blk, [pool.buy(2 * 10 ** 17, blk)])
    tiny = pool._log(10 ** 12, -1, blk + 2, RELAY, PID)                              # the sell came back with almost nothing: a tax, a trap
    at(e, blk + 2, [tiny])
    assert os.path.exists(E.HALT_FILE) and events("halt"), events("halt")
    pool2 = Pool()
    at(e, LB + 5000, [log_init(pid=PID2, blk=LB + 5000), log_ml(L0, blk=LB + 5000, pid=PID2), pool2.buy(5 * 10 ** 18, LB + 5000, pid=PID2)]); at(e, LB + 5002)
    at(e, LB + 5300, [pool2.buy(3 * 10 ** 16, LB + 5300, pid=PID2)])
    assert events("skip")[-1]["why"].startswith("halted"), events("skip")


@test
def live_buy_that_never_went_in():
    e, c = fresh(dry=False); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    b = e.sender.txs[0]; c.receipts = {b["hash"]: {"status": "0x0", "logs": []}}
    e.pos[PID]["sent_at"] -= 60
    at(e, LB + 400); drain(e)
    assert not e.pos and e.trades == 0 and events("skip")[-1]["why"] == "the buy did not go in", events("skip")


@test
def pull_while_open_sells():
    e, c = fresh(dry=False); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)]); at(e, LB + 302, [pool.buy(E.STAKE_WEI, LB + 302, sender=RELAY)])
    at(e, LB + 310, [log_ml(-L0, blk=LB + 310, i=99)])
    assert len(e.sender.txs) == 2 and events("exit")[0]["why"] == "the liquidity was pulled", events("exit")


@test
def daily_cap_and_one_position():
    e, c = fresh(MAX_TRADES_PER_DAY=0); pool = Pool(); launch(e, pool)
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    assert events("skip")[-1]["why"] == "daily cap"
    e, c = fresh(); pool = Pool(); launch(e, pool)
    e.pos["0x" + "ee" * 32] = {"state": "sent", "dry": True, "pid": "0x" + "ee" * 32}          # another pool's buy on its way
    e.pools["0x" + "ee" * 32] = dict(e.pools[PID], status="fired", hist=[])
    at(e, LB + 300, [pool.buy(3 * 10 ** 16, LB + 300)])
    assert events("skip")[-1]["why"] == "position open", events("skip")


@test
def recovery_sells_what_a_stopped_run_left():
    e, c = fresh(dry=False)
    with open(E.LOG_PATH, "w") as f:
        f.write(json.dumps({"ev": "fire", "pid": PID, "token": TOKEN, "sent": True, "stake": 0.01}) + "\n")
        f.write(json.dumps({"ev": "fire", "pid": "0x" + "ee" * 32, "token": TOKEN, "sent": True}) + "\n")
        f.write(json.dumps({"ev": "settled", "pid": "0x" + "ee" * 32}) + "\n")
    c.token_bal = 12345
    orig = e.sender.send
    def send(raw):
        ok, h = orig(raw); c.receipts[h] = {"status": "0x1", "logs": [{"address": E.PM, "topics": [E.T_SWAP, PID], "data": "0x" + w(9 * 10 ** 15) + w(-12345)}]}; return ok, h
    e.sender.send = send; E.time.sleep = lambda s: None
    e.recover()
    r = events("recovered"); assert len(r) == 1 and r[0]["status"] == "0x1" and abs(r[0]["eth_back"] - 0.009) < 1e-12, r
    assert len(e.sender.txs) == 1 and e.sender.txs[0]["data"][:8] == E.SEL_SELL and not os.path.exists(E.HALT_FILE)


if __name__ == "__main__":
    t0 = time.time(); n = 0
    only = sys.argv[1:]
    real_sleep = time.sleep
    for fn in TESTS:
        if only and fn.__name__ not in only:
            continue
        E.time.sleep = real_sleep
        fn(); n += 1
        print("ok", fn.__name__, flush=True)
    print(f"{n} tests passed in {time.time() - t0:.1f} s")
