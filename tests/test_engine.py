"""The flip engine against a scripted feed: real signed transactions in real L2 batch frames, the RPC and the sequencer stubbed.
A launch is armed from its receipt, the operator's first real-size buy fires the buy at the reserved nonce with the
predicted minOut, our own buy seen in the feed fixes the sell's block, the sell goes out at buy block + HOLD - LEAD, both
receipts make the trade_done line. Then the gates (dust, fee tier, late first buy, position open, daily cap), the dry run, stale
frames, a reverted buy. The exit (release 0.3): a buy behind ours that pays TAKE_PROFIT sells at once; one that does not leaves the deadline; the
pool's price follows every buy on the feed (a dust buy before the trigger moves minOut), buys that landed before the launch was
armed are replayed onto it; a pull at or before our sell halts live trading (the halt file) until it is removed; BUY_DELAY_BLOCKS;
the dry run's take-profit. Release 0.6: blocks with one transaction (kind 4) and nested batches; a lost reply to our buy;
a refused buy; a sell retried; our buy not seen in the feed; the time fallback; the 'sold none' halt and its restart read; the
sender's busy slot; a look-alike launcher in seat mode.
Plain script: python3 tests/test_engine.py"""
import os, sys, json, time, base64, tempfile, threading
import rlp
from eth_account import Account
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); LOG = tempfile.mktemp(suffix=".jsonl")
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY); RELAY = "0x" + "f1" * 20; LAUNCHER = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY, "LAUNCHERS": LAUNCHER, "STAKE_ETH": "0.0012",
                   "HOLD_BLOCKS": "4", "SELL_LEAD_BLOCKS": "2", "SELL_FALLBACK_S": "100", "FEE_MAX_PPM": "9999", "TRIGGER_MAX_BLOCKS": "150", "MAX_TRADES_PER_DAY": "2", "DAILY_STOP_USD": "15",
                   "TAKE_PROFIT": "0.01", "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt"})
os.environ.pop("FRONT_SELL_ON_ETH", None)                                                 # the code default (0 = off) is what 18m2 tests
sys.path.insert(0, os.path.join(ROOT, "src"))
import flip_engine as E
import v4math

PM = E.POOL_MANAGER; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"                  # the Universal Router: where the crowd's buys go
TOKEN = "0x" + "ab" * 20; PID = "0x" + "77" * 32; SQRT_P0 = 1292187213925453985058262482146976; TICK0 = 194000; LIQ = 61_310_000_000_000_000_000_000
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
RECEIPTS = {}; LOGS = []; SENT = []


# --- stubs
CODES = {}; NONCE_ON_CHAIN = ["0x5"]
def fake_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionReceipt": return RECEIPTS.get(params[0].lower())
    if method == "eth_getLogs": return LOGS
    if method == "eth_getTransactionCount": return NONCE_ON_CHAIN[0]
    if method == "eth_getCode": return CODES.get(params[0].lower(), "0x")
    if method == "eth_getBlockByNumber": return {"baseFeePerGas": hex(20_000_000), "number": "0x1"}
    if method == "eth_blockNumber": return hex(10 ** 9)                        # the node's head, far ahead: the pull check's range is never capped here
    raise RuntimeError(method)
E.rpc = fake_rpc


REPLIES = []                                                                   # scripted replies, oldest first; empty: every send accepted
class FakeSender:
    def post(self, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); SENT.append((i, raw))
        return REPLIES.pop(0) if REPLIES else {"result": "0x" + keccak(raw).hex()}
E.SENDER = FakeSender(); E.SIGNER = ACCT; E.state["nonce"] = 5; E.state["base_fee"] = 20_000_000
SYNC_BUY = [True]                                                              # the buy goes out on its own thread: the tests wait for its reply (15j: they do not)
_fire0 = E._fire
def _fire_sync(p, *a):
    _fire0(p, *a); pos = E.state["position"]
    if SYNC_BUY[0] and pos is not None and pos["pid"] == p["pid"] and not pos["dry"] and pos.get("buy_hash"):
        assert wait_for(lambda: "buy_reply" in pos), "no reply to the buy"
E._fire = _fire_sync


# --- the scripted chain
def signed(key, to, value, data, nonce):
    from eth_utils import to_checksum_address
    return bytes(Account.from_key(key).sign_transaction({"to": to_checksum_address(to), "value": value, "data": data, "gas": 300000, "gasPrice": 10 ** 8, "nonce": nonce, "chainId": 4663}).raw_transaction)


def frame(seq, raws, ts=None):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": ts or int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})


def launch_receipt(h, fee=1134, hooks="0" * 40):
    return {"status": "0x1", "blockNumber": "0x64", "logs": [
        {"address": PM, "topics": ["0x" + E.T_INIT, PID, "0x" + w(0), "0x" + w(TOKEN)], "data": "0x" + w(fee) + w(200) + w(hooks) + w(SQRT_P0) + w(TICK0)},
        {"address": PM, "topics": ["0x" + E.T_ML, PID, "0x" + w(ACCT.address)], "data": "0x" + w(-887200) + w(TICK0) + w(LIQ) + w(0)}]}


def swap_receipt(block, a0, a1, index=3, pid=None):
    return {"status": "0x1", "blockNumber": hex(block), "gasUsed": hex(120000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": hex(index),
            "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, pid or PID, "0x" + w(RELAY)], "data": "0x" + w(a0) + w(a1) + w(SQRT_P0) + w(LIQ) + w(0) + w(0)}]}


def events(ev=None):
    out = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
    return [e for e in out if ev is None or e["ev"] == ev]


def wait_for(cond, s=3.0):
    t0 = time.time()
    while time.time() - t0 < s:
        if cond(): return True
        time.sleep(0.01)
    return False


DEPLOYER = "0x" + "22" * 32; CROWD = "0x" + "33" * 32; OUTSIDER = "0x" + "44" * 32
BUY_DATA = "0x24856bc3" + w(0x40) + w(0x80) + w(1) + w(TOKEN) + w(3000)           # a router call that carries the token address


def do_launch(seq, fee=1134):
    raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), 0); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt(h, fee)
    E.ingest(frame(seq, [raw]))
    assert wait_for(lambda: PID in E.state["armed"]), "the launch was not armed"
    return E.state["armed"][PID]


def reset():
    E.state["armed"].clear(); E.state["position"] = None; E.state["trades_today"] = 0; E.state["pnl_today_usd"] = 0.0; E.state["seq"] = 0; SENT.clear(); RECEIPTS.clear()
    E.state["front_pnl_today_usd"] = 0.0; E.state["arming"].clear(); E.state["recent"].clear()     # a test's buys are never replayed onto a later test's launch
    E.state["front_nonbot_streak"] = {}


# --- 1. the live path
reset(); p = do_launch(100)
assert p["eligible"] and p["liq"] == LIQ and p["token"] == TOKEN[2:] and p["fee"] == 1134, p
for s in range(101, 131):
    E.ingest(frame(s, []))
trig_value = int(0.04e18); crowd = signed(CROWD, UR, trig_value, BUY_DATA, 7)
E.ingest(frame(131, [crowd]))
pos = E.state["position"]; assert pos is not None and pos["trig_seq"] == 131, "no fire on the first real buy"
fires = events("fire"); assert len(fires) == 1 and fires[0]["nonce"] == 5
assert len(SENT) == 1 and SENT[0][0] == 0
buy_raw = SENT[0][1]; f = rlp.decode(buy_raw); assert int.from_bytes(f[0], "big") == 5 and f[3].hex() == RELAY[2:]
data = f[5].hex(); assert data[:8] == E.SEL_BUY
x_trig = trig_value - (trig_value * 1134 + 999_999) // 1_000_000; sp1 = int(v4math.sqrt_after_buy(SQRT_P0, LIQ, x_trig)); expected = v4math.buy_out_int(sp1, LIQ, E.STAKE_WEI, 1134)
assert int(data[8 + 64*5: 8 + 64*6], 16) == E.STAKE_WEI and int(data[8 + 64*6: 8 + 64*7], 16) == int(expected * (1 - E.BUY_SLIP)), "stake or minOut wrong"
assert int(data[8 + 64*1: 8 + 64*2], 16) == int(TOKEN, 16) and int(data[8 + 64*2: 8 + 64*3], 16) == 1134 and int(data[8 + 64*3: 8 + 64*4], 16) == 200
assert E.state["nonce"] == 7
E.ingest(frame(132, [])); E.ingest(frame(133, [buy_raw]))              # our buy lands in block 133
assert pos["buy_seq"] == 133 and events("buy_seen")[-1]["offset"] == 2 and pos["feed_tokens"] == expected
E.ingest(frame(134, [])); assert not pos["sell_sent"]
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(133, -E.STAKE_WEI, expected); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(137, int(E.STAKE_WEI * 1.05), -expected)
E.ingest(frame(135, []))                                                 # 133 + 4 - 2: nobody bought behind us, the deadline sends the sell
assert pos["sell_sent"] and len(SENT) == 2 and SENT[1][0] == 1 and pos["sell_why"].startswith("deadline")
sf = rlp.decode(SENT[1][1]); assert int.from_bytes(sf[0], "big") == 6 and sf[5].hex()[:8] == E.SEL_SELL and int(sf[5].hex()[8 + 64*5: 8 + 64*6], 16) == 0
assert wait_for(lambda: events("trade_done")), "no trade_done"
d = events("trade_done")[-1]
assert d["buy"]["block"] == 133 and d["sell"]["block"] == 137 and d["hold_blocks"] == 4 and d["buy_offset"] == 2 and abs(d["ret"] - 0.05) < 1e-9 and d["pnl_usd"] > 0, d
assert d["pull_after_buy_blocks"] is None and d["pulled_before_sell"] is False and E.state["halted"] is None, d
assert E.state["position"] is None and E.state["trades_today"] == 1
print("ok live path: armed, fired at nonce 5 with the predicted minOut, the deadline sell at the buy block + 2 at nonce 6, trade_done priced")

# --- 2. gates
reset(); p = do_launch(200)
E.ingest(frame(205, [signed(OUTSIDER, UR, int(0.0001e18), BUY_DATA, 1)]))    # dust: no trigger
assert E.state["position"] is None and p["first_buy"] is None
E.ingest(frame(206, [signed(CROWD, TOKEN, int(0.05e18), "0x" + w(1), 8)]))   # a call to the token itself: not a buy
assert E.state["position"] is None
E.ingest(frame(360, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 9)]))          # 160 blocks after the launch: not the crowd
assert E.state["position"] is None and events("skip")[-1]["why"].startswith("late first buy")
reset(); p = do_launch(400, fee=20000)                                          # a 2% pool: outside the tier
assert not p["eligible"]
E.ingest(frame(430, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 10)]))
assert E.state["position"] is None and events("skip")[-1]["why"] == "pool not eligible"
reset(); p = do_launch(500); E.ingest(frame(530, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 11)]))
assert E.state["position"] is not None; E.state["trades_today"] = 2
pid2 = "0x" + "88" * 32; p2 = dict(p, pid=pid2, token="cd" * 20, token_bytes=bytes.fromhex("cd" * 20), first_buy=None, status="armed", launch_seq=525); E.state["armed"][pid2] = p2
E.ingest(frame(531, [signed(CROWD, UR, int(0.04e18), "0x24856bc3" + w("0x" + "cd" * 20), 12)]))
assert events("skip")[-1]["why"] == "position open"
E.state["position"] = None; p2["first_buy"] = None
E.ingest(frame(532, [signed(CROWD, UR, int(0.04e18), "0x24856bc3" + w("0x" + "cd" * 20), 13)]))
assert events("skip")[-1]["why"] == "daily cap"
print("ok gates: dust, token call, late first buy, fee tier, position open, daily cap")

# --- 3. the dry run
reset(); E.DRY_RUN = True; p = do_launch(600); E.ingest(frame(640, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 14)]))
pos = E.state["position"]; assert pos and pos["dry"] and events("would_fire")[-1]["plan_sell_seq"] == 646 and len(SENT) == 0
for s in range(641, 644):
    E.ingest(frame(s, []))
assert pos["buy_seq"] == 642 and pos["feed_tokens"] == pos["expected_tokens"] and not pos["sell_sent"]   # the planned landing: at the head of 642
E.ingest(frame(644, []))                                                       # 642 + 4 - 2
assert pos["sell_sent"] and events("would_sell")[-1]["seq"] == 644 and events("would_sell")[-1]["why"].startswith("deadline") and len(SENT) == 0
assert wait_for(lambda: E.state["position"] is None, 3.0)
E.state["trades_today"] = 0; pid3 = "0x" + "99" * 32; p3 = dict(p, pid=pid3, token="ef" * 20, token_bytes=bytes.fromhex("ef" * 20), first_buy=None, status="armed", launch_seq=650, sp=float(SQRT_P0), buys=0)
E.state["armed"][pid3] = p3; data3 = "0x24856bc3" + w("0x" + "ef" * 20)
E.ingest(frame(660, [signed(CROWD, UR, int(0.04e18), data3, 20)])); pos = E.state["position"]; assert pos and pos["pid"] == pid3
E.ingest(frame(661, [])); E.ingest(frame(662, [])); assert pos["buy_seq"] == 662 and not pos["sell_sent"]
E.ingest(frame(663, [signed(OUTSIDER, UR, int(0.04e18), data3, 2)]))            # the crowd's next buy behind our planned one: the dry run takes the profit
ws = events("would_sell")[-1]; assert pos["sell_sent"] and ws["seq"] == 663 and ws["why"].startswith("take profit") and ws["tp_ret"] > 0.01 and len(SENT) == 0, ws
assert wait_for(lambda: E.state["position"] is None, 3.0)
print("ok dry run: would_fire, the planned landing, would_sell at the deadline, and on a buy behind ours the take-profit; nothing sent")

# --- 4. a stale frame (the replay after a reconnect) trades nothing
reset(); E.DRY_RUN = True; p = do_launch(700); E.ingest(frame(730, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 15)], ts=int(time.time()) - 10))
assert E.state["position"] is None and p["first_buy"] == 730 and E.state["stale_blocks"] >= 1 and p["buys"] == 1
E.ingest(frame(735, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 16)]))            # fresh again: the crowd's next buy is not a trigger
assert E.state["position"] is None and p["buys"] == 2
print("ok stale frames: the first buy is recorded (and moves the price), nothing is fired on it or on the buys after it")


done_at = lambda n: [e for e in events("trade_done") if e.get("nonce") == n]          # a trade's line, by its nonce (a dry run's lands a second late)


# --- 5. a reverted buy (a crowd buy landed ahead of ours past BUY_SLIP): the presigned sell finds nothing, gas is the cost, no halt
reset(); E.DRY_RUN = False; E.state["nonce"] = 20; p = do_launch(800)
E.ingest(frame(830, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 16)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(831, [])); E.ingest(frame(832, [buy_raw])); E.ingest(frame(833, [])); E.ingest(frame(834, []))
assert pos["sell_sent"] and len(SENT) == 2
reverted = lambda block, gas: {"status": "0x0", "blockNumber": hex(block), "gasUsed": hex(gas), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
RECEIPTS["0x" + pos["buy_hash"]] = reverted(832, 40000); RECEIPTS["0x" + pos["sell_hash"]] = reverted(835, 30000)
assert wait_for(lambda: done_at(20)); d = done_at(20)[-1]
assert d["buy"]["status"] == "reverted" and d["sell"]["status"] == "reverted" and d["eth_in"] == 0 and d["gas_wei"] == 70000 * 20_000_000 and E.state["halted"] is None and E.state["position"] is None, d
print("ok a reverted buy: the presigned sell finds nothing to sell, the gas is the only cost, no halt")


# --- release 0.3: the exit, the feed's pool price, the halt
net = lambda x: x - (x * 1134 + 999_999) // 1_000_000
TRIG = int(0.04e18)


def relay_trade(seq_launch, nonce0, crowd_nonce):
    """a launch, the crowd's first buy 31 blocks in, our buy landing two blocks later; returns (pos, buy_raw, buy block)"""
    E.state["nonce"] = nonce0; p = do_launch(seq_launch); t = seq_launch + 31
    E.ingest(frame(t, [signed(CROWD, UR, TRIG, BUY_DATA, crowd_nonce)])); pos = E.state["position"]; assert pos is not None
    buy_raw = SENT[0][1]; E.ingest(frame(t + 1, [])); E.ingest(frame(t + 2, [buy_raw])); assert pos["buy_seq"] == t + 2
    return pos, buy_raw, t + 2


# --- 9. take profit: a buy behind ours that does not pay TAKE_PROFIT leaves the position; the one that does sells at once
reset(); E.DRY_RUN = False
pos, buy_raw, B = relay_trade(1200, 60, 30)
small, big = int(0.0001e18) * 3, int(0.04e18)
sp = v4math.sqrt_after_buy(v4math.sqrt_after_buy(float(SQRT_P0), LIQ, net(TRIG)), LIQ, net(E.STAKE_WEI)); gas = E.state["base_fee"] * 250_000
ret_after = lambda sp_: (v4math.sell_out_int(int(sp_), LIQ, pos["feed_tokens"], 1134) - E.STAKE_WEI - gas) / E.STAKE_WEI
sp_small = v4math.sqrt_after_buy(sp, LIQ, net(small)); sp_big = v4math.sqrt_after_buy(sp_small, LIQ, net(big))
assert ret_after(sp_small) < E.TAKE_PROFIT < ret_after(sp_big), (ret_after(sp_small), ret_after(sp_big))
E.HOLD_BLOCKS = 6                                                                    # the deadline at B + 4 here, so the two buys below come before it
E.ingest(frame(B + 1, [signed(OUTSIDER, UR, small, BUY_DATA, 6)])); assert not pos["sell_sent"], "sold on a buy that does not pay"
E.ingest(frame(B + 2, [signed(OUTSIDER, UR, big, BUY_DATA, 7)])); E.HOLD_BLOCKS = 4
assert pos["sell_sent"] and pos["sell_why"].startswith("take profit") and pos["sell_seq_sent"] == B + 2 and abs(pos["tp_ret"] - round(ret_after(sp_big), 4)) < 1e-12, (pos["sell_why"], pos["tp_ret"])
assert len(SENT) == 2 and rlp.decode(SENT[1][1])[5].hex()[:8] == E.SEL_SELL
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 3, int(E.STAKE_WEI * 1.07), -pos["feed_tokens"])
assert wait_for(lambda: done_at(60)); d = done_at(60)[-1]
assert d["sell_why"].startswith("take profit") and d["tp_ret"] == pos["tp_ret"] and d["sell_after_buy_blocks"] == 3 and d["pulled_before_sell"] is False, d
print("ok take profit: a buy behind ours worth less than TAKE_PROFIT leaves the position, the next one sells it in the same block, priced exactly")

# --- 10. the pool's price follows every buy on the feed: a dust buy before the trigger moves minOut
reset(); E.state["nonce"] = 70; p = do_launch(1300); dust = int(0.00005e18)
E.ingest(frame(1303, [signed(OUTSIDER, UR, dust, BUY_DATA, 8)]))
assert p["buys"] == 1 and p["first_buy"] is None and E.state["position"] is None
E.ingest(frame(1331, [signed(CROWD, UR, TRIG, BUY_DATA, 31)])); pos = E.state["position"]
sp_both = v4math.sqrt_after_buy(v4math.sqrt_after_buy(float(SQRT_P0), LIQ, net(dust)), LIQ, net(TRIG)); exp_both = v4math.buy_out_int(int(sp_both), LIQ, E.STAKE_WEI, 1134)
exp_trig_only = v4math.buy_out_int(int(v4math.sqrt_after_buy(SQRT_P0, LIQ, net(TRIG))), LIQ, E.STAKE_WEI, 1134)
assert pos["expected_tokens"] == exp_both < exp_trig_only and pos["min_out"] == int(exp_both * (1 - E.BUY_SLIP)), (pos["expected_tokens"], exp_both, exp_trig_only)
E.state["position"] = None
print("ok the feed's pool price: a dust buy before the trigger is in the prediction (the trigger-only one is too high, as it was by 4e-6 on every live trade)")

# --- 11. buys that landed before the launch was armed are replayed onto it; a first buy among them means no trade on that pool
reset(); E.state["nonce"] = 80
raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), 1); hl = "0x" + keccak(raw).hex()
E.ingest(frame(1400, [raw]))
E.ingest(frame(1403, [signed(OUTSIDER, UR, dust, BUY_DATA, 9)])); E.ingest(frame(1420, [signed(CROWD, UR, TRIG, BUY_DATA, 32)]))
assert PID not in E.state["armed"]
RECEIPTS[hl] = launch_receipt(hl); assert wait_for(lambda: PID in E.state["armed"])
p = E.state["armed"][PID]; assert p["buys"] == 2 and p["first_buy"] == 1420 and p["status"] == "late" and abs(p["sp"] - sp_both) / sp_both < 1e-15, p
E.ingest(frame(1423, [signed(CROWD, UR, TRIG, BUY_DATA, 33)])); assert E.state["position"] is None and p["buys"] == 3
print("ok arming after the first buy: the buys before it replayed onto the pool, the pool marked late, the next buy not traded")

# --- 12. a pull at or before our sell halts live trading (the halt file), until it is removed
reset()
pos, buy_raw, B = relay_trade(1500, 90, 34)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 5, 0, -pos["feed_tokens"], index=40)
LOGS[:] = [{"blockNumber": hex(B + 5), "transactionIndex": hex(12), "data": "0x" + w(-887200) + w(TICK0) + w(-LIQ) + w(0)}]
assert wait_for(lambda: done_at(90)); d = done_at(90)[-1]
assert d["pulled_before_sell"] is True and d["pull_after_buy_blocks"] == 5 and d["sell_after_buy_blocks"] == 5 and E.state["follow_halted"] and E.state["halted"] is None and os.path.exists(E.FOLLOW_HALT_FILE) and not os.path.exists(E.HALT_FILE), (d, E.state["follow_halted"])   # follow's pull halts follow only (front goes on)
assert any(e["what"].startswith("the follow strategy halted") for e in events("alarm"))
reset(); E.state["nonce"] = 95; p = do_launch(1600); E.ingest(frame(1631, [signed(CROWD, UR, TRIG, BUY_DATA, 35)]))
assert E.state["position"] is None and events("skip")[-1]["why"].startswith("halted"), events("skip")[-1]
E.state["follow_halted"] = None; os.remove(E.FOLLOW_HALT_FILE); LOGS.clear()
print("ok halt: the pull landed before our sell, the engine wrote the halt file and fires nothing more")

# --- 13. BUY_DELAY_BLOCKS: fire one block after the trigger if nothing else bought; skip if the crowd's next buy came first
reset(); E.BUY_DELAY_BLOCKS = 1; E.state["nonce"] = 100; p = do_launch(1700)
E.ingest(frame(1731, [signed(CROWD, UR, TRIG, BUY_DATA, 36)])); assert E.state["position"] is None and p["status"] == "delayed"
E.ingest(frame(1732, [])); pos = E.state["position"]
assert pos and pos["trig_seq"] == 1731 and pos["fire_seq"] == 1732 and pos["plan_buy_seq"] == 1734 and pos["expected_tokens"] == exp_trig_only, pos
E.state["position"] = None
reset(); p = do_launch(1800); E.ingest(frame(1831, [signed(CROWD, UR, TRIG, BUY_DATA, 37)])); E.ingest(frame(1832, [signed(CROWD, UR, TRIG, BUY_DATA, 38)]))
assert E.state["position"] is None and p["status"] == "skipped" and events("skip")[-1]["why"].startswith("a real buy landed between"), events("skip")[-1]
E.BUY_DELAY_BLOCKS = 0
print("ok BUY_DELAY_BLOCKS: fired one block after the trigger; skipped when the crowd's next buy came first")

# --- 14. ENTRY=seat: a launch through a launcher never seen before (known by its call), our buy at launch + 6, the burst behind it
E.ENTRY = "seat"; E.LAUNCH_SELECTORS = {"2fcb9108"}; FRESH = "0x" + "5e" * 20
OP_CODE = "0x" + "60806040" * 50; CODES[FRESH] = OP_CODE; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}   # the operator's launcher code, as the stub serves it


def seat_launch(seq, nonce, launcher=FRESH):
    raw = signed(DEPLOYER, launcher, 0, "0x2fcb9108" + w(1), nonce); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt(h)
    E.ingest(frame(seq, [raw])); assert wait_for(lambda: PID in E.state["armed"]), "a launch through a fresh launcher was not armed"
    return E.state["armed"][PID]


reset(); E.DRY_RUN = False; E.state["nonce"] = 110; p = seat_launch(1900, 2)
E.ingest(frame(1903, [signed(OUTSIDER, UR, int(0.000002e18), BUY_DATA, 10)]))        # the dust tester at + 3: below a real buy, the price moves
for s_ in (1904, 1905):
    E.ingest(frame(s_, [])); assert E.state["position"] is None, s_
E.ingest(frame(1906, [])); pos = E.state["position"]                                 # launch + 6: the seat fires
assert pos and pos["trig_seq"] == 1906 and pos["plan_buy_seq"] == 1908 and pos["trig_value"] == 0 and len(SENT) == 1, pos
sp_dust = v4math.sqrt_after_buy(float(SQRT_P0), LIQ, net(int(0.000002e18))); assert pos["expected_tokens"] == v4math.buy_out_int(int(sp_dust), LIQ, E.STAKE_WEI, 1134)
buy_raw = SENT[0][1]; E.ingest(frame(1907, [buy_raw])); assert pos["buy_seq"] == 1907
burst = [signed(CROWD, UR, int(0.08e18), BUY_DATA, 40), signed(OUTSIDER, UR, int(0.03e18), BUY_DATA, 11), signed(DEPLOYER, UR, int(0.07e18), BUY_DATA, 3)]
E.ingest(frame(1908, burst))                                                          # the burst, one block behind ours
assert pos["sell_sent"] and pos["sell_why"].startswith("take profit") and pos["sell_seq_sent"] == 1908 and pos["tp_ret"] > E.TAKE_PROFIT and len(SENT) == 2, (pos["sell_why"], pos["tp_ret"])
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(1907, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(1910, int(E.STAKE_WEI * 1.09), -pos["feed_tokens"])
assert wait_for(lambda: done_at(110)); d = done_at(110)[-1]; assert d["sell_why"].startswith("take profit") and d["sell_after_buy_blocks"] == 3 and E.state["halted"] is None, d
reset(); E.state["nonce"] = 120; p = seat_launch(2000, 3)
E.ingest(frame(2005, burst[:1]))                                                       # the burst before the seat: no trade
E.ingest(frame(2006, [])); E.ingest(frame(2007, []))
assert E.state["position"] is None and p["status"] == "late" and len(SENT) == 0
reset(); E.state["nonce"] = 130; FAKE = "0x" + "6f" * 20; CODES[FAKE] = "0x" + "fe" * 40   # a look-alike launcher: the same call, other code
p = seat_launch(2100, 4, launcher=FAKE)
assert not p["eligible"] and p["launcher_code"].startswith("unknown"), p["launcher_code"]
for s_ in range(2101, 2108):
    E.ingest(frame(s_, []))
assert E.state["position"] is None and len(SENT) == 0
reset(); E.state["nonce"] = 135; LAGGING = "0x" + "7a" * 20; CODES[LAGGING] = OP_CODE    # a node a few blocks behind: no code at 'latest' yet, the code at the launch's block
rpc0 = E.rpc
def lagging_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getCode" and params[1] == "latest": return "0x"
    return rpc0(method, params, tries, timeout)
E.rpc = lagging_rpc; p = seat_launch(2150, 5, launcher=LAGGING); E.rpc = rpc0
assert p["eligible"] and p["launcher_code"] == "operator", p["launcher_code"]
E.ENTRY = "follow"; E.LAUNCH_SELECTORS = set()
print("ok seat: a launch through a fresh launcher armed by its call, the buy at launch + 6, the burst one block behind it takes the profit; a burst before the seat, no trade; a look-alike launcher (other code) never traded")


# --- 15. release 0.6: the fixes from the review
def frame4(seq, raw, ts=None):
    """a block with one user transaction, as the sequencer sends it: a bare kind-4 message, no batch"""
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": ts or int(time.time())}, "l2Msg": base64.b64encode(b"\x04" + raw).decode()}}}]})


def nested(seq, raws):
    """a batch inside a batch"""
    inner = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    outer = b"\x03" + (len(inner)).to_bytes(8, "big") + inner
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(outer).decode()}}}]})


# 15a. a launch and our buy, each alone in its block (kind 4), and a trigger inside a nested batch: all seen
reset(); E.DRY_RUN = False; E.state["nonce"] = 140
raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), 5); hl = "0x" + keccak(raw).hex(); RECEIPTS[hl] = launch_receipt(hl)
E.ingest(frame4(2200, raw)); assert wait_for(lambda: PID in E.state["armed"]), "a launch alone in its block was missed"
E.ingest(nested(2231, [signed(CROWD, UR, TRIG, BUY_DATA, 50)])); pos = E.state["position"]; assert pos and pos["trig_seq"] == 2231, "a trigger in a nested batch was missed"
buy_raw = SENT[0][1]; E.ingest(frame(2232, [])); E.ingest(frame4(2233, buy_raw))
assert pos["buy_seq"] == 2233 and pos["feed_tokens"] == pos["expected_tokens"], "our buy alone in its block was missed"
E.ingest(frame(2234, [])); E.ingest(frame(2235, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(2233, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(2237, int(E.STAKE_WEI * 1.02), -pos["feed_tokens"])
assert wait_for(lambda: done_at(140)); assert E.state["halted"] is None
print("ok feed: a launch and our buy each alone in a block (kind 4), a trigger in a nested batch")

# 15b. no reply to our buy (transport failure): the position stays open; the buy lands; the sell goes on schedule
reset(); E.state["nonce"] = 150; p = do_launch(2300)
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}]
E.ingest(frame(2331, [signed(CROWD, UR, TRIG, BUY_DATA, 51)])); pos = E.state["position"]
assert pos is not None and pos.get("buy_reply_lost") and E.state["nonce"] == 152 and any("no reply to our buy" in e["what"] for e in events("alarm"))
buy_raw = SENT[0][1]; E.ingest(frame(2332, [])); E.ingest(frame(2333, [buy_raw])); E.ingest(frame(2334, [])); E.ingest(frame(2335, []))
assert pos["sell_sent"] and len(SENT) == 2
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(2333, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(2337, int(E.STAKE_WEI * 1.02), -pos["feed_tokens"])
assert wait_for(lambda: done_at(150)); d = done_at(150)[-1]; assert d["sell"]["status"] == "ok" and E.state["halted"] is None, d
print("ok a lost reply to our buy: the position kept, the buy seen in the feed, the sell on schedule, settled")

# 15c. the node refuses our buy: no sell, the position closed once the nonce is the chain's, the daily cap given back
reset(); E.state["nonce"] = 160; NONCE_ON_CHAIN[0] = hex(160); p = do_launch(2400)
REPLIES[:] = [{"error": {"code": -32000, "message": "insufficient funds for gas * price + value"}}]
fails = [2]; rpc0 = E.rpc
def flaky_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionCount" and fails[0] > 0:
        fails[0] -= 1; raise RuntimeError("timed out")
    return rpc0(method, params, tries, timeout)
E.rpc = flaky_rpc                                                                  # the nonce read fails twice: the position must stay open meanwhile
E.ingest(frame(2431, [signed(CROWD, UR, TRIG, BUY_DATA, 52)])); pos = E.state["position"]
assert pos is not None and wait_for(lambda: pos["sell_sent"]) and pos["sell_why"] == "buy refused" and E.state["position"] is pos
for s_ in range(2432, 2440):
    E.ingest(frame(s_, []))
assert wait_for(lambda: E.state["position"] is None) and fails[0] == 0 and events("buy_rejected") and E.state["trades_today"] == 0 and E.state["nonce"] == 160, E.state["nonce"]
assert len(SENT) == 1, "a sell went out behind a refused buy"
E.rpc = rpc0; NONCE_ON_CHAIN[0] = "0x5"
print("ok a refused buy: no sell, the nonce the chain's, the daily cap given back")

# 15d. no reply to our buy and it never went in: the sell is refused (nonce too high) and retried, the trade closes, the nonce comes back to the chain's
reset(); E.state["nonce"] = 170; NONCE_ON_CHAIN[0] = hex(170); p = do_launch(2500)
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}]
E.ingest(frame(2531, [signed(CROWD, UR, TRIG, BUY_DATA, 53)])); pos = E.state["position"]; assert pos and E.state["nonce"] == 172
nonce_high = {"error": {"code": -32000, "message": "nonce too high"}}; REPLIES[:] = [nonce_high] * E.SELL_TRIES
E.RECEIPT_TIMEOUT_S = 0.3
for s_ in range(2532, 2538):
    E.ingest(frame(s_, []))
assert pos["sell_sent"] and wait_for(lambda: done_at(170), 4.0), "no trade_done"
d = done_at(170)[-1]; assert d["buy"] == "no receipt" and E.state["halted"] is None, d
assert sum(1 for i, r in SENT if r == pos["sell_raw"]) == E.SELL_TRIES and any("not accepted" in e["what"] for e in events("alarm"))
assert E.state["nonce"] == 170 and E.state["trades_today"] == 0, (E.state["nonce"], E.state["trades_today"])     # set before trade_done is logged
E.RECEIPT_TIMEOUT_S = 25; NONCE_ON_CHAIN[0] = "0x5"
print("ok a lost buy that never went in: the sell retried and refused, the trade closed, the nonce back to the chain's, the daily cap given back")

# 15e. the first sell send fails (transport), the second goes in
reset(); E.state["nonce"] = 180; p = do_launch(2600)
E.ingest(frame(2631, [signed(CROWD, UR, TRIG, BUY_DATA, 54)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(2632, [])); E.ingest(frame(2633, [buy_raw])); E.ingest(frame(2634, []))
REPLIES[:] = [{"error": {"message": "send failed twice: connection reset"}}]
E.ingest(frame(2635, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(2633, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(2637, int(E.STAKE_WEI * 1.02), -pos["feed_tokens"])
assert wait_for(lambda: done_at(180)); ss = [e for e in events("sell_sent") if e["nonce"] == 181][-1]
assert ss["tries"] == 2 and [i for i, r in SENT if r == pos["sell_raw"]] == [1, 0], (ss, [i for i, r in SENT])
print("ok a failed sell send retried on the other connection")

# 15f. the feed never shows our buy: the sell goes on the planned block's deadline
reset(); E.state["nonce"] = 190; p = do_launch(2700)
E.ingest(frame(2731, [signed(CROWD, UR, TRIG, BUY_DATA, 55)])); pos = E.state["position"]
for s_ in (2732, 2733, 2734):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(2735, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline from the planned buy block")   # planned buy 2733 + 4 - 2
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(2734, -E.STAKE_WEI, pos["expected_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(2737, int(E.STAKE_WEI * 1.0), -pos["expected_tokens"])
assert wait_for(lambda: done_at(190))
print("ok our buy not seen in the feed: the sell on the planned block's deadline")

# 15g. the feed stalls: the wall-clock fallback sends the sell
reset(); E.state["nonce"] = 200; p = do_launch(2800)
E.ingest(frame(2831, [signed(CROWD, UR, TRIG, BUY_DATA, 56)])); pos = E.state["position"]
pos["fired_at"] -= 101; E.watchdog_tick()                                         # SELL_FALLBACK_S is 100 in these tests
assert pos["sell_sent"] and pos["sell_why"] == "time fallback"
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(2833, -E.STAKE_WEI, pos["expected_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(2836, int(E.STAKE_WEI * 1.0), -pos["expected_tokens"])
assert wait_for(lambda: done_at(200))
print("ok the feed stalls: the time fallback sends the sell")

# 15h. a filled buy whose sell sold nothing halts; the halt is read back after a restart
reset(); E.state["nonce"] = 210; pos, buy_raw, B = relay_trade(2900, 210, 57)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"])
RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x0", "blockNumber": hex(B + 4), "gasUsed": hex(30000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
assert wait_for(lambda: done_at(210)) and E.state["halted"] and "sold none" in E.state["halted"] and os.path.exists(E.HALT_FILE)
E.state["halted"] = None; E.load_halt(); assert E.state["halted"] and "sold none" in E.state["halted"], "the halt was not read back"
E.state["halted"] = None; os.remove(E.HALT_FILE)
print("ok a filled buy whose sell sold nothing: halted, and the halt read back after a restart")

# 15i. the sender: a slot held by the keepalive does not hold up a send
S = E.Sender.__new__(E.Sender); S.locks = [threading.Lock(), threading.Lock()]; S.conns = [None, None]; S.last = [0.0, 0.0]
S._oneoff = lambda body: {"result": "one-off"}; S._post_locked = lambda i, body, retry: {"result": "warm"}
assert S.post(1, "{}") == {"result": "warm"}
S.locks[1].acquire(); t0 = time.time(); r = S.post(1, "{}"); S.locks[1].release()
assert r == {"result": "one-off"} and time.time() - t0 < 0.5, r
assert E.reply_kind({"result": "0x1"}) == "ok" and E.reply_kind({"error": {"message": "send failed"}}) == "unknown"
assert E.reply_kind({"error": {"code": -32000, "message": "already known"}}) == "in" and E.reply_kind({"error": {"code": -32000, "message": "nonce too high"}}) == "rejected"
print("ok the sender: a busy slot falls back to a fresh connection at once; replies classified")

# 15j. a buy send that hangs (Nitro answers once the buy is in a block; a lost reply waits out its timeouts) holds up nothing
reset(); E.state["nonce"] = 240; NONCE_ON_CHAIN[0] = hex(242); p = do_launch(3200)
gate = threading.Event()
tx_nonce = lambda raw: int.from_bytes(rlp.decode(raw)[0], "big")
ours_at = lambda n: [r for _, r in list(SENT) if tx_nonce(r) == n]                # our transactions by nonce (a late send of the test before cannot pass for ours)
class HangingSender(FakeSender):
    def post(self, i, body, retry=True):
        r = super().post(i, body, retry)
        if tx_nonce(bytes.fromhex(json.loads(body)["params"][0][2:])) == 240:
            gate.wait(10)                                                      # the buy's reply: held until the sell is out
        return r
E.SENDER = HangingSender(); SYNC_BUY[0] = False
t0 = time.time(); E.ingest(frame(3231, [signed(CROWD, UR, TRIG, BUY_DATA, 61)])); pos = E.state["position"]
assert pos is not None and time.time() - t0 < 0.5 and E.state["nonce"] == 242, "the feed waited on the buy's reply"
assert wait_for(lambda: ours_at(240)); buy_raw = ours_at(240)[0]
E.ingest(frame(3232, [])); E.ingest(frame(3233, [buy_raw])); E.ingest(frame(3234, [])); E.ingest(frame(3235, []))
assert pos["buy_seq"] == 3233 and pos["sell_sent"] and "buy_reply" not in pos and wait_for(lambda: ours_at(241)), "the sell waited on the buy's reply"
gate.set(); assert wait_for(lambda: "buy_reply" in pos)
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(3233, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(3237, int(E.STAKE_WEI * 1.02), -pos["feed_tokens"])
assert wait_for(lambda: done_at(240)) and E.state["nonce"] == 242
E.SENDER = FakeSender(); SYNC_BUY[0] = True; NONCE_ON_CHAIN[0] = "0x5"
print("ok a buy send that hangs: the feed, our buy's landing and the sell on schedule go on without its reply")

# 15k. the nonce read fails for a while after a trade: the position stays open (no trade on a wrong nonce) until the chain answers
reset(); E.state["nonce"] = 250; NONCE_ON_CHAIN[0] = hex(252); pos, buy_raw, B = relay_trade(3300, 250, 62)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, [])); assert pos["sell_sent"]
fails = [3]; rpc0 = E.rpc
def flaky_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionCount" and fails[0] > 0:
        fails[0] -= 1; raise RuntimeError("timed out")
    return rpc0(method, params, tries, timeout)
E.rpc = flaky_rpc; E.state["nonce"] = 999                                         # a nonce gone wrong: settle must put the chain's in
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 4, int(E.STAKE_WEI * 1.02), -pos["feed_tokens"])
assert wait_for(lambda: done_at(250), 6.0) and fails[0] == 0 and E.state["nonce"] == 252 and E.state["position"] is None, (fails, E.state["nonce"])
E.rpc = rpc0; NONCE_ON_CHAIN[0] = "0x5"
print("ok a nonce read that fails for a while: retried, the position kept until the chain's nonce is in")

# --- 16. ENTRY=auto: the original launcher gets the follow entry (its crowd 40-60 blocks in), a per-launch copy the seat
E.ENTRY = "auto"; E.LAUNCH_SELECTORS = {"2fcb9108"}; E.SEAT_CODE_HASHES = set(E.LAUNCHER_CODE_HASHES)
reset(); E.state["nonce"] = 220; p = do_launch(4000)                                    # through the original launcher (LAUNCHERS)
assert p["entry"] == "follow" and p["eligible"]
for s_ in range(4001, 4010):
    E.ingest(frame(s_, [])); assert E.state["position"] is None, "the follow entry fired before the crowd"
E.ingest(frame(4046, [signed(CROWD, UR, TRIG, BUY_DATA, 60)])); pos = E.state["position"]; assert pos and pos["trig_seq"] == 4046, "no follow fire on the crowd first buy"
E.state["position"] = None
reset(); E.state["nonce"] = 230; p = seat_launch(4100, 6)                             # through a per-launch copy
assert p["entry"] == "seat" and p["eligible"]
for s_ in range(4101, 4106):
    E.ingest(frame(s_, []))
E.ingest(frame(4106, [])); pos = E.state["position"]; assert pos and pos["trig_seq"] == 4106 and pos["trig_value"] == 0, "no seat fire at launch + 6"
E.state["position"] = None; E.ENTRY = "follow"; E.LAUNCH_SELECTORS = set()
print("ok auto: the original launcher follows the crowd's first buy, a per-launch copy takes the seat at launch + 6")

# --- 17. release 0.9: the front strategy (a volume bot's 2.4333285 ETH launches), armed from the launch's own calldata
FX = json.load(open(os.path.join(ROOT, "tests", "data", "front_launch.json")))           # a real launch from the chain, with its Initialize and ModifyLiquidity values
d = E.decode_launch(bytes.fromhex(FX["input"][2:]))
assert d and d["pid"] == FX["pid"] and "0x" + d["token"] == FX["token"] and d["fee"] == FX["fee"] and d["tick_spacing"] == FX["tick_spacing"] and d["sqrt_p"] == FX["sqrt_p"], d
assert d["mint_liq"] == FX["liq"] and d["lo"] == FX["lo"] and d["hi"] == FX["hi"] and E.tick_at(d["sqrt_p"]) == FX["tick0"] and d["c0"] == "0" * 40 and d["hooks"] == "0" * 40
assert E.decode_launch(b"\xac\x96\x50\xd8" + b"\x00" * 64) is None and E.decode_launch(bytes.fromhex(FX["input"][2:])[:600]) is None
print("ok front: the launch decoded from its calldata alone matches the chain (pool id, key, price, tick, liquidity, range)")

POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; FPID = FX["pid"]; FTOKEN = FX["token"]; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
FBUY = "0xc1120e3d" + w(FTOKEN) + w(0) * 8                                               # the volume bot's buy: ETH as value, the token in its calldata
E.FRONT = True; E.FRONT_DRY_RUN = False; E.MAX_TRADES_PER_DAY = 50; E.FRONT_MAX_PER_DAY = 50; E.LAUNCH_SELECTORS = set(); E.ENTRY = "auto"; LOGS[:] = []
def front_launch(seq, nonce):
    raw = signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], nonce)
    E.ingest(frame(seq, [raw])); return E.state["armed"].get(FPID)
reset(); E.state["nonce"] = 300; p = front_launch(5000, 3)
assert p and p["entry"] == "front" and p["eligible"] and p["liq"] == FX["liq"] and p["launch_seq"] == 5000, p
pos = E.state["position"]
assert pos and pos["entry"] == "front" and pos["stake"] == E.FRONT_STAKE_WEI and pos["trig_seq"] == 5000 and len(SENT) == 1 and pos["send_after"] == E.FRONT_HOLD_BLOCKS, pos
bf = rlp.decode(SENT[0][1]); assert int.from_bytes(bf[0], "big") == 300 and bf[5].hex()[8 + 64*5: 8 + 64*6] == w(E.FRONT_STAKE_WEI)   # amountIn = the front stake
assert pos["expected_tokens"] == v4math.buy_out_int(int(float(FX["sqrt_p"])), FX["liq"], E.FRONT_STAKE_WEI, 2500)   # the engine keeps the price as a float, as for follow
buy_raw = SENT[0][1]; dust = signed(OUTSIDER, "0x" + "65" * 20, int(0.00011e18), FBUY, 30)   # a launch dust sniper (below a real buy)
E.ingest(frame(5001, [dust, buy_raw])); assert pos["buy_seq"] == 5001 and not pos["sell_sent"] and p["first_buy"] is None
for s_ in range(5002, 5009):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_                            # the hold is 12 blocks, not the follow's 2
E.ingest(frame(5009, [signed(CROWD, BOT, int(0.12e18), FBUY, 70)]))                      # the volume bot's first buy, + 9
assert pos["sell_sent"] and pos["sell_why"].startswith("take profit") and pos["sell_seq_sent"] == 5009 and pos["tp_ret"] > 0.05 and len(SENT) == 2, (pos["sell_why"], pos["tp_ret"])
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(5001, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(5010, int(E.FRONT_STAKE_WEI * 1.09), -pos["feed_tokens"], pid=FPID)
assert wait_for(lambda: done_at(300)); d = done_at(300)[-1]; assert d["entry"] == "front" and d["ret"] > 0.08 and E.state["front_halted"] is None and E.state["front_today"] == 1, d
print("ok front: armed in the launch block from the feed, fired at once at the front stake, held past the follow's 2 blocks, sold on the volume bot's first buy")

# 17c. no bot buy: the sell goes at our buy + FRONT_HOLD_BLOCKS
reset(); E.state["nonce"] = 310; p = front_launch(5100, 3); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(5101, [buy_raw]))
for s_ in range(5102, 5101 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(5101 + E.FRONT_HOLD_BLOCKS, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline"), pos.get("sell_why")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(5101, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(5101 + E.FRONT_HOLD_BLOCKS + 1, int(E.FRONT_STAKE_WEI * 0.995), -pos["feed_tokens"], pid=FPID)
assert wait_for(lambda: done_at(310))
print("ok front: no volume-bot buy, the sell at our buy + FRONT_HOLD_BLOCKS")

# 17d. a pull before our front sell halts the front strategy only; follow keeps trading; a new front launch is skipped
reset(); E.state["nonce"] = 320; p = front_launch(5200, 3); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(5201, [buy_raw]))
for s_ in range(5202, 5209):
    E.ingest(frame(s_, []))
E.ingest(frame(5209, [signed(CROWD, BOT, int(0.12e18), FBUY, 71)])); assert pos["sell_sent"]
LOGS[:] = [{"blockNumber": hex(5206), "transactionIndex": hex(1), "data": "0x" + w(-887250) + w(887250) + w(-FX["liq"]) + w(0)}]   # the operator pulled at + 5
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(5201, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x1", "blockNumber": hex(5210), "gasUsed": hex(135200), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2",
                                     "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, FPID, "0x" + w(RELAY)], "data": "0x" + w(1) + w(-pos["feed_tokens"]) + w(1) + w(1) + w(0) + w(0)}]}
assert wait_for(lambda: done_at(320)) and E.state["front_halted"] and E.state["halted"] is None and os.path.exists(E.FRONT_HALT_FILE), (E.state["front_halted"], E.state["halted"])
LOGS[:] = []
reset(); E.state["nonce"] = 330; p = front_launch(5300, 4); assert E.state["position"] is None and any("halted" in e.get("why", "") for e in events("skip")[-3:])
reset(); E.state["nonce"] = 330; p = do_launch(5400); E.ingest(frame(5431, [signed(CROWD, UR, TRIG, BUY_DATA, 72)])); pos = E.state["position"]
assert pos and pos["entry"] == "follow" and len(SENT) == 1, "follow stopped by a front halt"
E.state["position"] = None
E.state["front_halted"] = None; os.remove(E.FRONT_HALT_FILE); E.load_halt(); assert E.state["front_halted"] is None
print("ok front: a pull before our front sell halts the front strategy only (its own file); follow keeps trading")

# 17e. too late: the position was open through launch + FRONT_FIRE_MAX: no trade on that pool
reset(); E.state["nonce"] = 340; E.state["position"] = {"pid": "x", "dry": False, "entry": "follow", "sell_sent": True, "buy_seq": 1, "buy_hash": None, "fired_at": time.monotonic(), "plan_buy_seq": 1, "send_after": 2}
p = front_launch(5500, 3)
for s_ in range(5501, 5501 + E.FRONT_FIRE_MAX):
    E.ingest(frame(s_, []))
E.state["position"] = None; E.ingest(frame(5501 + E.FRONT_FIRE_MAX, [])); assert p["status"] == "late" and len(SENT) == 0, p["status"]
print("ok front: a front launch not fired by launch + FRONT_FIRE_MAX is left alone")

# 17f. front dry run while follow is live: the dry front trade logs, and a live follow trade drops it
E.FRONT_DRY_RUN = True
reset(); E.state["nonce"] = 350; p = front_launch(5600, 3); fpos = E.state["position"]
assert fpos and fpos["dry"] and len(SENT) == 0 and events("would_fire")[-1]["entry"] == "front"
reset_keep = E.state["position"]; E.state["armed"].pop(FPID, None)
p = do_launch(5700); E.state["position"] = reset_keep
E.ingest(frame(5731, [signed(CROWD, UR, TRIG, BUY_DATA, 73)])); pos = E.state["position"]
assert pos is not fpos and pos["entry"] == "follow" and not pos["dry"] and len(SENT) == 1 and any("dropped" in e.get("why", "") for e in events("skip")[-3:])
E.state["position"] = None; E.FRONT = False; E.FRONT_DRY_RUN = True; E.ENTRY = "follow"
print("ok front: in its own dry run the front strategy logs its decisions and never holds up a live follow trade")

# --- 18. release 0.9's review: each strategy its own daily stop and halts; the launch's full fingerprint; nothing in the front path
# can cost follow a block or the slot
E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"; LOGS[:] = []; SNIPER = "0x" + "65" * 20
def front_close(pos, buy_seq, sell_seq, back):
    RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(buy_seq, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
    RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(sell_seq, back, -pos["feed_tokens"], pid=FPID)
    assert wait_for(lambda: done_at(pos["nonce"])); return done_at(pos["nonce"])[-1]

# 18a. front against its own daily stop, follow against its own; a front loss goes to front's day only
reset(); E.state["nonce"] = 400; E.state["front_pnl_today_usd"] = -E.FRONT_DAILY_STOP_USD - 0.01
front_launch(6000, 3); assert E.state["position"] is None and events("skip")[-1]["why"] == "daily stop"
reset(); E.state["nonce"] = 400; E.state["pnl_today_usd"] = -E.DAILY_STOP_USD - 0.01
front_launch(6010, 3); pos = E.state["position"]; assert pos and pos["entry"] == "front" and pos["pnl_key"] == "front_pnl_today_usd", "front stopped by follow's day"
E.ingest(frame(6011, [SENT[0][1]]))
for s_ in range(6012, 6012 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
d = front_close(pos, 6011, 6024, int(E.FRONT_STAKE_WEI * 0.99))
assert E.state["pnl_today_usd"] == -E.DAILY_STOP_USD - 0.01 and E.state["front_pnl_today_usd"] == d["pnl_usd"] < 0, (E.state["pnl_today_usd"], E.state["front_pnl_today_usd"])
reset(); E.state["nonce"] = 405; E.state["front_pnl_today_usd"] = -E.FRONT_DAILY_STOP_USD - 0.01
do_launch(6050); E.ingest(frame(6081, [signed(CROWD, UR, TRIG, BUY_DATA, 79)])); pos = E.state["position"]
assert pos and pos["entry"] == "follow", "follow stopped by front's day"
E.state["position"] = None
print("ok front: each strategy has its own daily stop; a front loss counts in front's day only")

# 18b. a front sell that sold nothing halts the front strategy only
reset(); E.state["nonce"] = 410
front_launch(6100, 3); pos = E.state["position"]; E.ingest(frame(6101, [SENT[0][1]]))
for s_ in range(6102, 6102 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(6101, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x0", "blockNumber": hex(6114), "gasUsed": hex(50000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x1", "logs": []}
assert wait_for(lambda: done_at(410)) and wait_for(lambda: E.state["front_halted"] is not None)
assert "sold none" in E.state["front_halted"] and E.state["halted"] is None and not os.path.exists(E.HALT_FILE) and os.path.exists(E.FRONT_HALT_FILE), (E.state["front_halted"], E.state["halted"])
E.state["front_halted"] = None; os.remove(E.FRONT_HALT_FILE)
print("ok front: a front sell that sold nothing halts the front strategy only")

# 18c. a front-shaped launch with a bad price (sqrtPriceX96 0): not armed; another price: armed and marked new (not armed with FRONT_PIN=1);
# the rest of the block goes on
FIN = bytes.fromhex(FX["input"][2:]); assert FIN[328:360] == int(FX["sqrt_p"]).to_bytes(32, "big")
bad0 = FIN[:328] + b"\x00" * 32 + FIN[360:]; other = FIN[:328] + (int(FX["sqrt_p"]) + 1).to_bytes(32, "big") + FIN[360:]
assert E.decode_launch(bad0) is None and E.decode_launch(other)["sqrt_p"] == int(FX["sqrt_p"]) + 1
reset(); E.state["nonce"] = 420; do_launch(6200)
E.ingest(frame(6231, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, "0x" + bad0.hex(), 5), signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, "0x" + other.hex(), 6),
                      signed(CROWD, UR, TRIG, BUY_DATA, 80)]))
pos = E.state["position"]; assert pos and pos["entry"] == "follow" and pos["trig_seq"] == 6231, "the block was lost after a bad front launch"
assert events("launch_undecoded")[-1]["seq"] == 6231
a = [e for e in events("armed") if e["seq"] == 6231]; assert len(a) == 1 and a[0]["eligible"] and a[0]["fingerprint"].startswith("new: launch price") and FPID in E.state["armed"], a
E.state["position"] = None
reset(); E.FRONT_PIN = True; E.ingest(frame(6240, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, "0x" + other.hex(), 7)])); E.FRONT_PIN = False
a = events("armed")[-1]; assert a["seq"] == 6240 and not a["eligible"] and "FRONT_PIN" in a["why"] and FPID not in E.state["armed"] and E.state["position"] is None, a
FAM0 = E.FRONT_FAMILIES[E.FRONT_VALUE_WEI]
d = dict(E.decode_launch(FIN)); assert E.front_mismatch(d, d["mint_liq"], FAM0) is None and E.front_fingerprint(d, FAM0) == []
for k, v, why in (("fee", 10000, "fee"), ("hooks", "11" * 20, "hook")):
    assert why in E.front_mismatch({**d, k: v}, d["mint_liq"], FAM0), (k, E.front_mismatch({**d, k: v}, d["mint_liq"], FAM0))
assert E.front_mismatch(d, 0, FAM0) and E.front_mismatch({**d, "fee": 3000}, d["mint_liq"], FAM0) == "fee 3000" and E.front_fingerprint({**d, "fee": 3000, "tick_spacing": 60, "mint_liq": 1}, FAM0) == ["tick spacing 60", "liquidity 1"]
print("ok front: a bad launch is not armed and follow's block goes on; a new price, liquidity or tick spacing is traded and marked (FRONT_PIN=1: not)")

# 18d. an error anywhere in one transaction skips that transaction only
reset(); E.state["nonce"] = 430; do_launch(6300)
real_arm_front = E.arm_front; E.arm_front = lambda *a: 1 / 0
E.ingest(frame(6331, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], 7), signed(CROWD, UR, TRIG, BUY_DATA, 81)]))
E.arm_front = real_arm_front
pos = E.state["position"]; assert pos and pos["entry"] == "follow" and pos["trig_seq"] == 6331 and any("failed to process" in str(e.get("what")) for e in events("alarm")[-3:])
E.state["position"] = None
print("ok an error in one transaction skips it alone: the rest of the block (here follow's trigger) goes on")

# 18e. the same pool again is not armed twice; a dry front position is dropped only for a live trade that really fires
E.FRONT_DRY_RUN = True; reset(); E.state["nonce"] = 440
p = front_launch(6400, 8); fpos = E.state["position"]; assert fpos and fpos["dry"]
assert front_launch(6401, 9) is p and any("already armed" in e.get("why", "") for e in events("skip")[-3:])
E.state["armed"].pop(FPID); E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(6402); E.ingest(frame(6403, [signed(CROWD, UR, TRIG, BUY_DATA, 82)]))
assert E.state["position"] is fpos and events("skip")[-1]["why"] == "daily cap" and not any("dropped" in e.get("why", "") for e in events("skip")[-3:])
E.FRONT_DRY_RUN = False; E.state["position"] = None
print("ok front: a pool is armed once; a dry front position stays when the live trade does not pass its gates")

# 18f. buys ahead of ours: a sniper's small buy leaves room (we fire); 0.01 ETH ahead does not (late)
reset(); E.state["nonce"] = 460; E.state["trades_today"] = 0
E.ingest(frame(6700, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], 11), signed(OUTSIDER, SNIPER, int(0.0005e18), FBUY, 31)]))
pos = E.state["position"]; assert pos and pos["entry"] == "front" and E.state["armed"][FPID]["first_buy"] == 6700, "a small buy in the launch block made the pool late"
E.state["position"] = None
reset(); E.state["nonce"] = 470
E.ingest(frame(6800, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], 12), signed(OUTSIDER, SNIPER, int(0.01e18), FBUY, 32)]))
assert E.state["position"] is None and E.state["armed"][FPID]["status"] == "late" and "too much ETH" in events("skip")[-1]["why"]
print("ok front: a small buy ahead of ours leaves room for the bot's buy; 0.01 ETH ahead makes the pool late")

# 18g. the bot's buy that reverts (too much ahead of it): no phantom take-profit, the pool's price unmoved, the sell at once
reset(); E.state["nonce"] = 480
front_launch(6900, 13); pos = E.state["position"]; p = E.state["armed"][FPID]
E.ingest(frame(6901, [signed(OUTSIDER, SNIPER, int(0.015e18), FBUY, 33), SENT[0][1]]))    # 0.015 ETH lands ahead of our buy, after we fired
assert pos["buy_seq"] == 6901 and not pos["sell_sent"]
sp_before = p["sp"]; E.ingest(frame(6909, [signed(CROWD, BOT, int(0.05e18), FBUY, 74)]))
assert pos["sell_sent"] and pos["sell_why"].startswith("the bot's buy reverts") and pos["tp_ret"] is None and p["sp"] == sp_before, (pos.get("sell_why"), pos["tp_ret"])
r = events("front_bot_reverts")[-1]; assert r["quote_ratio"] < E.FRONT_BOT_MINOUT and r["ours"], r
front_close(pos, 6901, 6911, int(E.FRONT_STAKE_WEI * 0.99))
print("ok front: the bot's buy that cannot meet its minOut is no take-profit: the pool unmoved, the sell at once")

# 18h. follow has the slot first: a live front trade waits while a follow launch waits for its crowd (or its receipt is on its way)
reset(); E.state["nonce"] = 490
do_launch(7000); front_launch(7010, 14); assert E.state["position"] is None and "slot first" in events("skip")[-1]["why"]
E.ingest(frame(7031, [signed(CROWD, UR, TRIG, BUY_DATA, 83)])); pos = E.state["position"]; assert pos and pos["entry"] == "follow"
reset(); E.state["nonce"] = 495; E.state["arming"].add("0xpending"); front_launch(7100, 15); assert E.state["position"] is None and "slot first" in events("skip")[-1]["why"]
reset(); E.state["nonce"] = 495; do_launch(7200); front_launch(7200 + E.TRIGGER_MAX_BLOCKS + 1, 16); pos = E.state["position"]
assert pos and pos["entry"] == "front", "a follow launch past its trigger window still held the slot"
E.state["position"] = None
print("ok front: follow has the slot first (a follow launch waiting for its crowd or its receipt); past its window, front trades")

# 18i. the relay's balance: a front-only shortfall at start turns front off, follow starts; at run time a stake above it is skipped
def rpc_checks(method, params, tries=4, timeout=10):
    if method == "eth_chainId": return hex(4663)
    if method == "eth_getCode": return "0x6080"
    if method == "eth_call": return "0x" + w(ACCT.address) if params[0]["data"] == "0x" + E.SEL_OWNER else "0x" + w(E.POOL_MANAGER)
    if method == "eth_getBalance": return hex(int(0.0015e18))
    return fake_rpc(method, params)
E.rpc = rpc_checks; real_sender = E.Sender; E.Sender = lambda url: FakeSender(); E.FRONT_STAKE_ETH = 0.002; E.FRONT_STAKE_WEI = int(0.002e18); E.state["front_halted"] = None
E.checks(); assert E.state["front_halted"] and "front stake" in E.state["front_halted"] and E.state["halted"] is None and E.state["relay_wei"] == int(0.0015e18) and not os.path.exists(E.FRONT_HALT_FILE)
E.state["front_halted"] = None; E.FRONT_STAKE_ETH = 0.0; E.FRONT_STAKE_WEI = 0
E.checks(); assert E.state["front_halted"] and "above 0" in E.state["front_halted"]
E.rpc = fake_rpc; E.Sender = real_sender; E.SENDER = FakeSender(); E.FRONT_STAKE_ETH = 0.0012; E.FRONT_STAKE_WEI = int(0.0012e18); E.state["front_halted"] = None
reset(); E.state["nonce"] = 500; E.state["relay_wei"] = int(0.001e18); do_launch(7300); E.ingest(frame(7331, [signed(CROWD, UR, TRIG, BUY_DATA, 84)]))
assert E.state["position"] is None and "relay holds less" in events("skip")[-1]["why"]
E.state["relay_wei"] = None
print("ok the relay: a front-only shortfall at start turns front off and follow starts; at run time a stake above the relay's balance is skipped")

# 18j. the time fallback acts on the position it looked at only; a zero stake is a zero stake
a_ = {"pid": "a", "sell_sent": False, "dry": True}; b_ = {"pid": "b", "sell_sent": False, "dry": True}
E.state["position"] = b_; E.send_sell("time fallback", a_); assert not a_["sell_sent"] and not b_["sell_sent"]
E.state["position"] = None
tx = E.tx_buy({"c0": "0" * 40, "token": "ab" * 20, "fee": 2500, "tick_spacing": 50, "hooks": "0" * 40}, 1, 0, 0, 0); assert tx["data"][2 + 8 + 64*5: 2 + 8 + 64*6] == w(0)
print("ok a sell sent for a position no longer in the slot does nothing; tx_buy's stake 0 is 0")

# 18k. a live front trade frees the slot once both receipts are in: follow trades during its pull check, front waits for it, and the
# nonce follow reserved survives the front's settle; the relay's balance moves by the trade
reset(); E.state["nonce"] = 520; E.PULL_WATCH_S = 1.0; chain0 = NONCE_ON_CHAIN[0]; NONCE_ON_CHAIN[0] = hex(522); E.state["relay_wei"] = int(0.01e18)
front_launch(7500, 17); fpos = E.state["position"]; E.ingest(frame(7501, [SENT[0][1]]))
for s_ in range(7502, 7502 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
assert fpos["sell_sent"]
back = int(E.FRONT_STAKE_WEI * 1.08)
RECEIPTS["0x" + fpos["buy_hash"]] = swap_receipt(7501, -E.FRONT_STAKE_WEI, fpos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + fpos["sell_hash"]] = swap_receipt(7515, back, -fpos["feed_tokens"], pid=FPID)
assert wait_for(lambda: E.state["position"] is None and E.state["front_settling"] is fpos), "the front trade kept the slot through its pull check"
E.state["armed"].pop(FPID); front_launch(7520, 18); assert E.state["position"] is None and "pull check" in events("skip")[-1]["why"]
E.state["armed"].pop(FPID); do_launch(7600); E.ingest(frame(7631, [signed(CROWD, UR, TRIG, BUY_DATA, 85)])); pos = E.state["position"]
assert pos and pos["entry"] == "follow" and pos["nonce"] == 522 and E.state["nonce"] == 524, (pos and pos["nonce"], E.state["nonce"])
assert wait_for(lambda: done_at(520)) and E.state["front_settling"] is None and E.state["nonce"] == 524 and E.state["position"] is pos, E.state["nonce"]
assert E.state["relay_wei"] == int(0.01e18) + back - E.FRONT_STAKE_WEI, E.state["relay_wei"]
E.state["position"] = None; E.PULL_WATCH_S = 0; NONCE_ON_CHAIN[0] = chain0; E.state["relay_wei"] = None
print("ok front: out of the slot once its receipts are in; follow trades during its pull check at the next nonce, kept through the front's settle")

# 18l. front yields only to a follow launch that follow can trade (not at its daily cap); a launch whose arming thread never started leaves nothing behind
reset(); E.state["nonce"] = 530; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(7700); front_launch(7705, 19); pos = E.state["position"]; assert pos and pos["entry"] == "front", "front yielded to a follow launch follow cannot trade"
E.state["position"] = None; E.state["trades_today"] = 0
real_start = threading.Thread.start
def bad_start(self):
    if getattr(self, "_target", None) is E.arm_launch_thread:
        raise RuntimeError("can't start new thread")
    return real_start(self)
reset(); threading.Thread.start = bad_start
try:
    E.ingest(frame(7800, [signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(2), 1)]))
finally:
    threading.Thread.start = real_start
assert not E.state["arming"], E.state["arming"]
print("ok front: it yields only to a follow launch follow can trade; a launch whose arming never started does not block front")

# 18m. a decoy-size buy behind ours is no exit; the bot's buy is, even too small for the take-profit (in its quick-pull hours the pull comes 2-4 blocks after it)
reset(); E.state["nonce"] = 540
front_launch(7900, 20); pos = E.state["position"]; E.ingest(frame(7902, [SENT[0][1]]))
E.ingest(frame(7903, [signed(OUTSIDER, SNIPER, int(0.00012e18), FBUY, 34)])); assert not pos["sell_sent"], pos.get("sell_why")
E.ingest(frame(7910, [signed(CROWD, BOT, int(0.008e18), FBUY, 75)]))
assert pos["sell_sent"] and pos["sell_why"].startswith("the bot's buy behind ours") and pos["tp_ret"] is not None and pos["tp_ret"] < E.FRONT_TAKE_PROFIT, (pos.get("sell_why"), pos["tp_ret"])
front_close(pos, 7902, 7911, int(E.FRONT_STAKE_WEI * 0.999))
print("ok front: a decoy behind ours is no exit; the bot's buy sells at once even below the take-profit")

# 18m2. Oct 10's two -100% trades: the bot bought 0.00495 ETH (its smallest size, under the old 0.005 sell-on threshold), the pull came 3 blocks
# later, our sell waited for the deadline. Now a buy through the bot's router behind ours sells at once whatever its size; the operator's decoys
# (2e-6, 0.00012, then 0.001485 and 0.00495 ETH on Oct 10 afternoon) do not, whatever their size, because the size rule is off by default
# (FRONT_SELL_ON_ETH 0); set, it sells on any buy of that size
reset(); E.state["nonce"] = 545
front_launch(7950, 22); pos = E.state["position"]; E.ingest(frame(7951, [SENT[0][1]]))
E.ingest(frame(7953, [signed(OUTSIDER, UR, int(0.000002e18), FBUY, 35), signed(OUTSIDER, SNIPER, int(0.00012e18), FBUY, 36)])); assert not pos["sell_sent"], pos.get("sell_why")
E.ingest(frame(7959, [signed(CROWD, BOT, int(0.00495e18), FBUY, 76)]))
assert pos["sell_sent"] and pos["sell_why"].startswith("the bot's buy behind ours (0.00495 ETH)") and pos["sell_seq_sent"] == 7959 and pos["tp_ret"] is not None and pos["tp_ret"] < 0, (pos.get("sell_why"), pos["tp_ret"])
assert E.state["armed"][FPID]["bot_seq"] == 7959, "a small buy through the bot's router was not taken for the bot's buy"
front_close(pos, 7951, 7960, int(E.FRONT_STAKE_WEI * 0.998))
reset(); E.state["nonce"] = 550; assert E.FRONT_SELL_ON_WEI == 0, "the size rule must be off by default"
front_launch(7970, 23); pos = E.state["position"]; E.ingest(frame(7971, [SENT[0][1]]))
E.ingest(frame(7975, [signed(OUTSIDER, SNIPER, int(0.001485e18), FBUY, 37), signed(OUTSIDER, SNIPER, int(0.00495e18), FBUY, 38)])); assert not pos["sell_sent"], pos.get("sell_why")   # the decoys of Oct 10 15:04 and 15:45
sell_on0 = E.FRONT_SELL_ON_WEI; E.FRONT_SELL_ON_WEI = int(0.004e18)                                                                # the size rule, when set
E.ingest(frame(7977, [signed(OUTSIDER, SNIPER, int(0.0045e18), FBUY, 40)])); E.FRONT_SELL_ON_WEI = sell_on0
assert pos["sell_sent"] and pos["sell_why"].startswith("a real-size buy behind ours (0.00450 ETH, not through the bot's router)") and E.state["armed"][FPID]["bot_seq"] is None, pos.get("sell_why")
front_close(pos, 7971, 7977, int(E.FRONT_STAKE_WEI * 0.998))
reset(); E.state["nonce"] = 555                                                          # before our fire, a small buy through the router is the bot's: the pool is late
E.ingest(frame(7980, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], 24), signed(CROWD, BOT, int(0.00495e18), FBUY, 77)]))
assert E.state["position"] is None and E.state["armed"][FPID]["status"] == "late" and "the bot's buy came first" in events("skip")[-1]["why"], events("skip")[-1]
print("ok front: the bot's buy is known by its router at any size (0.00495 ETH, the Oct 10 losses) and sells at once; the size rule is off by default (the decoys matched every threshold) and works when set")

# 18m4. the bot's buy lands in our own block ahead of our buy (small enough to pass our minOut): the pull is 2-4 blocks away, so the position sells
# the moment our buy is seen, not at the deadline
reset(); E.state["nonce"] = 557
front_launch(7990, 26); pos = E.state["position"]; p = E.state["armed"][FPID]
E.ingest(frame(7991, [signed(CROWD, BOT, int(0.02e18), FBUY, 78), SENT[0][1]]))
assert p["bot_seq"] == 7991 and pos["buy_seq"] == 7991 and pos["sell_sent"] and pos["sell_why"].startswith("the bot's buy landed ahead of ours in the same block"), (pos.get("sell_why"), p["bot_seq"])
front_close(pos, 7991, 7992, int(E.FRONT_STAKE_WEI * 1.01))
print("ok front: the bot's buy ahead of ours in our own block sells at once, not at the deadline")

# 18m3. follow's near-miss halt: the operator's pull within FOLLOW_NEAR_MISS_BLOCKS (4) of our buy, behind our sell, halts follow only (its own
# file); front keeps trading; a pull one block later is not a near miss. The exit survives a pull at our buy + 4 or later only (protect/exits_bt.out).
reset(); E.state["armed"].pop(FPID, None); LOGS[:] = []
pos, buy_raw, B = relay_trade(8100, 600, 90)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 3, int(E.STAKE_WEI * 0.995), -pos["feed_tokens"], index=2)
LOGS[:] = [{"blockNumber": hex(B + 4), "transactionIndex": hex(1), "data": "0x" + w(-887200) + w(TICK0) + w(-LIQ) + w(0)}]
assert wait_for(lambda: done_at(600)); d = done_at(600)[-1]
assert d["pulled_before_sell"] is False and d["pull_after_buy_blocks"] == 4 and d["sell_after_buy_blocks"] == 3 and d.get("near_miss") is True, d
assert E.state["follow_halted"] and E.state["follow_halted"].startswith("near miss") and E.state["halted"] is None and E.state["front_halted"] is None, (E.state["follow_halted"], E.state["halted"])
assert os.path.exists(E.FOLLOW_HALT_FILE) and not os.path.exists(E.HALT_FILE) and any(e["what"].startswith("the follow strategy halted") for e in events("alarm")[-3:])
LOGS[:] = []
reset(); E.state["nonce"] = 610; do_launch(8200); E.ingest(frame(8231, [signed(CROWD, UR, TRIG, BUY_DATA, 91)]))
assert E.state["position"] is None and events("skip")[-1]["why"].startswith("halted: near miss"), events("skip")[-1]
E.state["armed"].pop(PID, None); front_launch(8240, 25); fpos = E.state["position"]; assert fpos and fpos["entry"] == "front", "front stopped by follow's near-miss halt"
E.state["position"] = None
E.state["follow_halted"] = None; os.remove(E.FOLLOW_HALT_FILE); E.load_halt(); assert E.state["follow_halted"] is None
reset(); E.state["armed"].pop(FPID, None)
pos, buy_raw, B = relay_trade(8300, 620, 92)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, [])); assert pos["sell_sent"]
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 3, int(E.STAKE_WEI * 0.995), -pos["feed_tokens"], index=2)
LOGS[:] = [{"blockNumber": hex(B + 5), "transactionIndex": hex(1), "data": "0x" + w(-887200) + w(TICK0) + w(-LIQ) + w(0)}]
assert wait_for(lambda: done_at(620)); d = done_at(620)[-1]
assert d["pull_after_buy_blocks"] == 5 and not d.get("near_miss") and E.state["follow_halted"] is None and E.state["halted"] is None, d
LOGS[:] = []
print("ok follow: a pull within 4 blocks of our buy, behind our sell, halts follow only (its own file); front keeps trading; a pull at + 5 does not")
E.FRONT = False; E.ENTRY = "follow"

# 18n. a restart keeps the day: today's live trades read back from the log (counts and P&L per strategy); yesterday's and dry ones are not
log0 = E.LOG_PATH; E.LOG_PATH = LOG + ".day"; now_t = time.time(); y_t = now_t - 86400
with open(E.LOG_PATH, "w") as f:
    for t_, entry, pnl, buy in ((now_t, "follow", -2.5, {"status": "ok"}), (now_t, "front", 0.6, {"status": "ok"}), (now_t, "front", -5.7, {"status": "ok"}),
                                (now_t, "front", 0.0, "no receipt"), (y_t, "front", -9.0, {"status": "ok"})):
        f.write(json.dumps({"ev": "trade_done", "dry": False, "entry": entry, "pnl_usd": pnl, "buy": buy, "t": t_}, separators=(",", ":")) + "\n")
    f.write(json.dumps({"ev": "trade_done", "dry": True, "pid": "x", "t": now_t}, separators=(",", ":")) + "\n")
E.state.update({"trades_today": 0, "front_today": 0, "pnl_today_usd": 0.0, "front_pnl_today_usd": 0.0}); E.roll_day(); got = E.restore_today(); os.remove(E.LOG_PATH); E.LOG_PATH = log0
if E.today() == time.strftime("%Y-%m-%d", time.gmtime(now_t)):                       # not across midnight
    assert got == {"trades_today": 1, "front_today": 2, "pnl_today_usd": -2.5, "front_pnl_today_usd": 0.6 - 5.7}, got
    assert E.state["front_pnl_today_usd"] <= -E.FRONT_DAILY_STOP_USD, "front's day not kept"
E.state.update({"trades_today": 0, "front_today": 0, "pnl_today_usd": 0.0, "front_pnl_today_usd": 0.0})
print("ok a restart keeps the day: today's live trades read back per strategy (counts and P&L), so the daily caps and stops hold")

# 18o. a stop (SIGTERM) mid-trade: no new trade, the open one still sells on schedule and settles, then the engine exits; a trade
# still open after STOP_WAIT_S exits with an alarm
exits = []; E.EXIT = lambda c: exits.append(c); E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
reset(); E.state["nonce"] = 560; E.state["stopping"] = None; E.state["stop_logged"] = False
front_launch(8000, 21); pos = E.state["position"]; assert pos and pos["entry"] == "front"
E.on_stop(15, None); E.stop_tick(); assert not exits and events("stopping")[-1]["position"] == pos["pid"]
E.state["armed"].pop(PID, None); do_launch(8001); E.ingest(frame(8031, [SENT[0][1], signed(CROWD, UR, TRIG, BUY_DATA, 86)]))
assert E.state["position"] is pos and events("skip")[-1]["why"].startswith("stopping"), events("skip")[-1]
for s_ in range(8032, 8032 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
assert pos["sell_sent"] and pos["sell_why"].startswith("deadline"), pos.get("sell_why")
E.stop_tick(); assert not exits, "exited before the open trade settled"
front_close(pos, 8031, 8031 + E.FRONT_HOLD_BLOCKS + 1, int(E.FRONT_STAKE_WEI * 0.995))
assert wait_for(lambda: E.state["position"] is None and E.state["front_settling"] is None)
E.stop_tick(); assert exits == [0] and events("stopped")[-1]["idle"] is True, exits
exits.clear(); E.state.update({"stopping": None, "stop_logged": False, "position": {"pid": "0xstuck", "sell_sent": True}})
E.on_stop(15, None); stop_wait0 = E.STOP_WAIT_S; E.STOP_WAIT_S = 0.0; time.sleep(0.01); E.stop_tick()
assert exits == [0] and events("stopped")[-1]["idle"] is False and "still open" in events("alarm")[-1]["what"]
E.STOP_WAIT_S = stop_wait0; E.EXIT = os._exit; E.state.update({"stopping": None, "stop_logged": False, "position": None}); E.FRONT = False; E.ENTRY = "follow"
print("ok a stop mid-trade: no new trade, the open one sells on schedule and settles, then the engine exits (with an alarm after STOP_WAIT_S)")

# 18p. the stop's load-bearing waits: front's pull check (front_settling) holds the exit; with nothing open a front launch during the
# stop is still refused; the watchdog's real loop keeps stop_tick running when watchdog_tick raises
exits = []; E.EXIT = lambda c: exits.append(c); E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
reset(); E.state["nonce"] = 570; E.state.update({"stopping": None, "stop_logged": False, "front_settling": None})
held = threading.Event(); rpc0 = E.rpc
def held_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getLogs":
        held.wait(30)                                                                   # front's pull check in progress (the test releases it)
    return rpc0(method, params, tries, timeout)
E.rpc = held_rpc
front_launch(8100, 22); pos = E.state["position"]; assert pos and pos["entry"] == "front"
E.ingest(frame(8101, [SENT[0][1]]))
for s_ in range(8102, 8102 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
assert pos["sell_sent"]
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(8101, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(8101 + E.FRONT_HOLD_BLOCKS + 1, int(E.FRONT_STAKE_WEI * 1.05), -pos["feed_tokens"], pid=FPID)
assert wait_for(lambda: E.state["front_settling"] is pos and E.state["position"] is None), "front did not leave the slot for its pull check"
import signal; sig0 = signal.signal(signal.SIGTERM, E.on_stop); os.kill(os.getpid(), signal.SIGTERM)   # the real signal path, as main() installs it
assert wait_for(lambda: E.state["stopping"] is not None); signal.signal(signal.SIGTERM, sig0); E.stop_tick()
assert not exits and events("stopping")[-1]["front_settling"] is True, "exited during front's pull check"
held.set(); assert wait_for(lambda: done_at(570) and E.state["front_settling"] is None)
E.rpc = rpc0; n_sent = len(SENT); E.state["armed"].pop(FPID, None)
front_launch(8200, 23)                                                                  # nothing open, stopping: the gate alone must refuse it
assert E.state["position"] is None and len(SENT) == n_sent and events("skip")[-1]["why"].startswith("stopping"), events("skip")[-1]
for s_ in range(8201, 8201 + E.FRONT_FIRE_MAX + 1):
    E.ingest(frame(s_, []))
assert sum(1 for e in events("skip") if e.get("seq", 0) >= 8200 and e["why"].startswith("stopping")) == 1, "one skip line per launch refused by the stop"
E.stop_tick(); assert exits == [0] and events("stopped")[-1]["idle"] is True, exits
exits.clear(); E.state.update({"stopping": None, "stop_logged": False, "position": None}); E.state["armed"].pop(FPID, None)
def exit_thread(c):
    exits.append(c); raise SystemExit                                                  # ends the watchdog thread as os._exit would end the process
wt0 = E.watchdog_tick; E.watchdog_tick = lambda: 1 / 0; E.EXIT = exit_thread
wd = threading.Thread(target=E.watchdog, daemon=True); wd.start(); time.sleep(0.1)
assert wd.is_alive() and not exits, "a raising watchdog_tick killed the watchdog"
E.on_stop(15, None); assert wait_for(lambda: exits == [0], 2.0), "stop_tick did not run after watchdog_tick raised"
E.watchdog_tick = wt0; E.EXIT = os._exit; E.state.update({"stopping": None, "stop_logged": False, "position": None, "front_settling": None}); E.FRONT = False; E.ENTRY = "follow"
print("ok a stop waits for front's pull check, refuses a front launch with nothing open, and survives a raising watchdog_tick")

# 18q. a stop never waits on a failing nonce re-read (the next start reads the chain's count): a finished trade's record is written and
# the engine exits idle at once; a refused buy whose nonce read is failing exits at once too, with no alarm
exits = []; E.EXIT = lambda c: exits.append(c); E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
reset(); E.state["nonce"] = 580; E.state.update({"stopping": None, "stop_logged": False, "front_settling": None}); E.state["armed"].pop(FPID, None)
rpc0 = E.rpc
def nonce_down(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionCount":
        raise RuntimeError("eth_getTransactionCount: 429")
    return rpc0(method, params, tries, timeout)
E.rpc = nonce_down
front_launch(8300, 24); pos = E.state["position"]; assert pos and pos["entry"] == "front"
E.ingest(frame(8301, [SENT[0][1]])); E.on_stop(15, None)
for s_ in range(8302, 8302 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
d = front_close(pos, 8301, 8301 + E.FRONT_HOLD_BLOCKS + 1, int(E.FRONT_STAKE_WEI * 1.05))            # trade_done written although the nonce read fails
assert wait_for(lambda: E.state["front_settling"] is None and E.state["position"] is None, 10.0), "the stop waited on the nonce re-read"
E.stop_tick(); assert exits == [0] and events("stopped")[-1]["idle"] is True and not [e for e in events("alarm") if "still open" in e["what"] and e.get("pid") == pos["pid"]]
exits.clear(); E.state.update({"stopping": None, "stop_logged": False}); reset(); E.state["nonce"] = 590; E.state["armed"].pop(FPID, None)
REPLIES[:] = [{"error": {"code": -32005, "message": "429 Too Many Requests"}}]
front_launch(8400, 25); pos = E.state["position"]; assert pos and wait_for(lambda: pos.get("buy_rejected") and pos.get("sell_why") == "buy refused")
E.on_stop(15, None); assert wait_for(lambda: E.state["position"] is None, 10.0), "a refused buy held the stop for its nonce read"
E.stop_tick(); assert exits == [0] and events("stopped")[-1]["idle"] is True and E.state["nonce"] == 590 and len(SENT) == 1
E.rpc = rpc0; REPLIES[:] = []; E.EXIT = os._exit; E.state.update({"stopping": None, "stop_logged": False, "position": None, "front_settling": None}); E.FRONT = False; E.ENTRY = "follow"
print("ok a stop never waits on a failing nonce read: the trade's record is written and the engine exits idle; a refused buy exits at once")

# 18r. eth_getLogs failing (the pull check unreadable): the settle still writes trade_done and the 'sold none' halt (792a8c5's `pulls`)
reset(); E.state["nonce"] = 6600; E.state["front_halted"] = None; E.state["armed"].pop(FPID, None); E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
rpc0 = E.rpc
def logs_down(method, params, tries=4, timeout=10):
    if method == "eth_getLogs":
        raise RuntimeError("eth_getLogs: query timeout")
    return rpc0(method, params, tries, timeout)
E.rpc = logs_down
front_launch(8500, 26); pos = E.state["position"]; assert pos and pos["entry"] == "front"
E.ingest(frame(8501, [SENT[0][1]]))
for s_ in range(8502, 8502 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(8501, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x0", "blockNumber": hex(8520), "gasUsed": hex(30000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
assert wait_for(lambda: done_at(6600)), [e.get("what") for e in events("alarm")][-2:]
assert done_at(6600)[-1].get("pull_check") and E.state["front_halted"] and "sold none" in E.state["front_halted"], E.state["front_halted"]
assert [e for e in events("alarm") if e["what"].startswith("pull check unreadable") and e.get("pid") == pos["pid"]], "no alarm for the unreadable pull check"
E.rpc = rpc0; E.state["front_halted"] = None; os.remove(E.FRONT_HALT_FILE); E.FRONT = False; E.ENTRY = "follow"
print("ok the pull check unreadable: the trade's record and the 'sold none' halt are still written")

# --- 19. FEED_HEADERS: the handshake headers of an authenticated feed, as JSON or "Name: value; Name: value"; empty = none
assert E.parse_headers("") == {} and E.parse_headers("   ") == {}
assert E.parse_headers('{"Authorization": "Bearer abc", "X-Key": "k1"}') == {"Authorization": "Bearer abc", "X-Key": "k1"}
assert E.parse_headers("Authorization: Bearer abc; X-Key: k1") == {"Authorization": "Bearer abc", "X-Key": "k1"}
assert E.parse_headers("Authorization: Bearer a:b:c") == {"Authorization": "Bearer a:b:c"} and E.FEED_HEADERS == {}
print("ok FEED_HEADERS: an authenticated feed's handshake headers parse from JSON or 'Name: value' pairs; none by default")
os.remove(LOG)

# --- 20. front families: the bot's 3.0 ETH line beside the 2.4333 one (FRONT_FAMILIES), each with its own fingerprint, fee bound, room and exit
W32 = lambda v: v.to_bytes(32, "big")
def relaunch(fee, ts, sqrt_p, liq):
    """the fixture's launch calldata with another PoolKey fee and tick spacing, launch price and mint liquidity (both PoolKey copies)"""
    d0 = E.decode_launch(FIN); key = bytes.fromhex(d0["c0"]).rjust(32, b"\0") + bytes.fromhex(d0["token"]).rjust(32, b"\0") + W32(d0["fee"]) + W32(d0["tick_spacing"]) + bytes.fromhex(d0["hooks"]).rjust(32, b"\0")
    assert FIN.count(key) == 2, FIN.count(key)
    i1 = FIN.find(key); i2 = FIN.find(key, i1 + 1); b = bytearray(FIN)
    nk = key[:64] + W32(fee) + W32(ts) + key[128:]
    b[i1:i1 + 160] = nk; b[i1 + 160:i1 + 192] = W32(sqrt_p); b[i2:i2 + 160] = nk; b[i2 + 224:i2 + 256] = W32(liq)
    lo, hi = -887200 // ts * ts, 887200 // ts * ts                                       # a range the chain would accept: multiples of the tick spacing
    b[i2 + 160:i2 + 192] = (lo % 2 ** 256).to_bytes(32, "big"); b[i2 + 192:i2 + 224] = (hi % 2 ** 256).to_bytes(32, "big")
    return bytes(b)
V3_VALUE = 3 * 10 ** 18; V3_SQRT = 679394651928963067279918579724198; V3_LIQ = 25725498245903809899643
E.FRONT_FAMILIES[V3_VALUE] = {**FAM0, "name": "v3", "value_wei": V3_VALUE, "fee": 10000, "tick_spacing": 200, "sqrt_p": V3_SQRT, "liq": V3_LIQ, "bot_minout": 0.95, "ahead_max_wei": int(0.07e18),
                               "take_profit": 9.0, "hold_blocks": 20, "stake_wei": int(0.0058e18), "dry_run": False, "pin": False}
assert E.FEE_MAX_PPM < 10000, "the test needs follow's fee bound below 1%: front's own bound must let the 1% family through"
E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
reset(); E.state["nonce"] = 700; E.state["front_halted"] = None
d3 = E.decode_launch(relaunch(10000, 200, V3_SQRT, V3_LIQ)); assert d3["fee"] == 10000 and d3["tick_spacing"] == 200 and d3["sqrt_p"] == V3_SQRT and d3["mint_liq"] == V3_LIQ and d3["pid"] != FPID, d3
E.ingest(frame(9000, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 3)]))
p3 = E.state["armed"].get(d3["pid"]); assert p3 and p3["fam"] == "v3" and p3["eligible"] and p3["fee"] == 10000 and events("launch")[-1]["fam"] == "v3", (p3 and p3.get("eligible"), events("armed")[-1])
pos = E.state["position"]; assert pos and pos["fam"] == "v3" and pos["stake"] == int(0.0058e18) and pos["send_after"] == 20 and pos["tp"] == 9.0 and pos["pid"] == d3["pid"], pos
bf = rlp.decode(SENT[0][1]); assert bf[5].hex()[8 + 64*5: 8 + 64*6] == w(int(0.0058e18)), "the buy's amountIn is the family's stake"
E.ingest(frame(9001, [SENT[0][1]])); assert pos["buy_seq"] == 9001
for s_ in range(9002, 9006):
    E.ingest(frame(s_, [signed(OUTSIDER, SNIPER, int(0.003e18), FBUY, 40 + s_)]))        # 0.003 ETH outsiders behind ours (0.012 in the pool with ours): no take-profit at 9, no size rule
    assert not pos["sell_sent"], s_
for s_ in range(9006, 9009):
    E.ingest(frame(s_, []))
E.ingest(frame(9009, [signed(CROWD, BOT, int(0.12e18), FBUY, 80)]))                                                             # the bot's buy through its router: with 0.0058 ahead the 0.95 minOut holds (no revert) and it is the exit
assert not events("front_bot_reverts") or events("front_bot_reverts")[-1]["seq"] != 9009, "the 3.0 line's 0.95 minOut must survive our stake ahead"
assert pos["sell_sent"] and pos["sell_why"].startswith("the bot's buy behind ours"), pos.get("sell_why")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(9001, -int(0.0058e18), pos["feed_tokens"], pid=d3["pid"])
RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(9010, int(0.0058e18 * 1.06), -pos["feed_tokens"], pid=d3["pid"])
assert wait_for(lambda: done_at(700)); d = done_at(700)[-1]; assert d["entry"] == "front" and d["fam"] == "v3" and d["ret"] > 0.04 and d["nonbot_streak"] == 0, d
reset(); E.state["nonce"] = 710; front_launch(9100, 4); q = E.state["armed"].get(FPID); assert q and q["fam"] == "v2.433" and E.state["position"]["fam"] == "v2.433"   # the 2.4333 line, unchanged
reset(); E.state["nonce"] = 720; E.FRONT_FAMILIES[V3_VALUE]["pin"] = True
E.ingest(frame(9200, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, int(FX["sqrt_p"]), V3_LIQ).hex(), 5)]))
a = events("armed")[-1]; assert a["fam"] == "v3" and not a["eligible"] and "new fingerprint" in a["why"] and "launch price" in a["why"], a   # the 2.4333 price on a 3.0 launch: the family's pin
E.FRONT_FAMILIES[V3_VALUE]["pin"] = False; assert not E.FRONT_PIN
E.FRONT_FAMILIES[V3_VALUE]["dry_run"] = True; E.state["armed"].clear(); E.state["position"] = None; n_sent = len(SENT)
E.ingest(frame(9205, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 5)]))
assert E.state["position"] and E.state["position"]["dry"] and len(SENT) == n_sent and events("would_fire")[-1]["fam"] == "v3", "a family's own dry run"   # this family dry, the other live
E.FRONT_FAMILIES[V3_VALUE]["dry_run"] = False; E.state["position"] = None; E.state["armed"].clear()
E.ingest(frame(9206, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(2500, 50, V3_SQRT, V3_LIQ).hex(), 6)]))
a = events("armed")[-1]; assert a["fam"] == "v3" and not a["eligible"] and a["why"] == "front: fee 2500", a                           # another fee: front's own bound, pin or not
E.ingest(frame(9207, [signed(DEPLOYER, POSM, 4 * 10 ** 18, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 7)]))
assert events("launch")[-1]["seq"] == 9206, "a 4.0 ETH launch is no family: not a front launch"
del E.FRONT_FAMILIES[V3_VALUE]; reset()
print("ok front families: the 3.0 ETH line arms and trades beside the 2.4333 one with its own fee bound (1%), price pin, stake, hold, 0.95 minOut and take-profit")

# 20b. the decoy signal: FRONT_NONBOT_HALT live front exits in a row not into the bot's buy halt front; the bot's buy resets the count
E.FRONT_NONBOT_HALT = 3; reset(); E.state["front_halted"] = None; E.state["nonce"] = 730
def front_deadline_trade(seq, nonce):
    E.state["armed"].pop(FPID, None); front_launch(seq, nonce); pos = E.state["position"]; E.ingest(frame(seq + 1, [SENT[-1][1]]))
    for s_ in range(seq + 2, seq + 2 + E.FRONT_HOLD_BLOCKS):
        E.ingest(frame(s_, []))
    assert pos["sell_sent"] and pos["sell_why"].startswith("deadline"); d = front_close(pos, seq + 1, seq + 1 + E.FRONT_HOLD_BLOCKS + 1, int(E.FRONT_STAKE_WEI * 0.997)); return d
def front_bot_trade(seq, nonce):
    E.state["armed"].pop(FPID, None); front_launch(seq, nonce); pos = E.state["position"]; E.ingest(frame(seq + 1, [SENT[-1][1]])); E.ingest(frame(seq + 8, [signed(CROWD, BOT, int(0.12e18), FBUY, 90 + nonce)]))
    assert pos["sell_sent"] and pos.get("bot_exit") and pos["sell_why"].startswith("take profit"), pos.get("sell_why")   # the 1% take-profit fires on the bot's buy: a paying exit
    return front_close(pos, seq + 1, seq + 9, int(E.FRONT_STAKE_WEI * 1.09))
d1 = front_deadline_trade(9300, 5); E.state["nonce"] = 732; d2 = front_bot_trade(9400, 6); E.state["nonce"] = 734; d3_ = front_deadline_trade(9500, 7); E.state["nonce"] = 736; d4 = front_deadline_trade(9600, 8)
E.restore_today(); assert E.state["front_nonbot_streak"].get("v2.433") == 2 and not [e for e in events("nonbot_streak_reset") if e["t"] >= d4["t"]], "a run that halted nothing must not reset"
assert d2["bot_exit"] and not d1["bot_exit"] and (d1["nonbot_streak"], d2["nonbot_streak"], d3_["nonbot_streak"], d4["nonbot_streak"]) == (1, 0, 1, 2) and E.state["front_halted"] is None, (d1["nonbot_streak"], d2["nonbot_streak"], d3_["nonbot_streak"], d4["nonbot_streak"])
E.state["nonce"] = 738; d5 = front_deadline_trade(9700, 9)
assert d5["nonbot_streak"] == 3 and d5.get("nonbot_halted") and E.state["front_halted"] and "3 v2.433 front trades in a row paid under +2%" in E.state["front_halted"] and E.state["halted"] is None and os.path.exists(E.FRONT_HALT_FILE), E.state["front_halted"]
E.state["nonce"] = 740; E.state["armed"].pop(FPID, None); front_launch(9800, 10); assert E.state["position"] is None and "halted" in events("skip")[-1]["why"], events("skip")[-1]
got = E.restore_today(); assert E.state["front_nonbot_streak"].get("v2.433") == 3 and got["front_today"] >= 5, (E.state["front_nonbot_streak"], got)   # the run goes on across a restart
os.remove(E.FRONT_HALT_FILE); E.restore_today()                                          # the owner cleared the halt: the run starts again at the next start
assert E.state["front_nonbot_streak"].get("v2.433") == 0 and events("nonbot_streak_reset")[-1]["was"] == 3, E.state["front_nonbot_streak"]
E.state["front_halted"] = None; E.FRONT_NONBOT_HALT = 5; reset(); E.FRONT = False; E.ENTRY = "follow"
print("ok the decoy signal: 3 live front exits in a row that paid under +2% halt front (its own file, per family, restored at a restart); a paying exit resets the count")

# 20c. the FRONT_FAMILIES parser: the runbook's JSON, and every wrong input refused at start
V3_JSON = '[{"name":"v3.0","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"25725498245903809899643","bot_minout":0.95,"ahead_max_eth":0.07,"take_profit":9,"hold_blocks":20,"stake_eth":0.002,"dry_run":true,"pin":true}]'
os.environ["FRONT_FAMILIES"] = V3_JSON; fams = E.front_families(); os.environ.pop("FRONT_FAMILIES")
assert set(fams) == {E.FRONT_VALUE_WEI, 3 * 10 ** 18} and fams[3 * 10 ** 18]["name"] == "v3.0" and fams[3 * 10 ** 18]["stake_wei"] == int(0.002e18) and fams[3 * 10 ** 18]["dry_run"] and fams[3 * 10 ** 18]["pin"] \
    and fams[3 * 10 ** 18]["ahead_max_wei"] == int(0.07e18) and fams[3 * 10 ** 18]["sqrt_p"] == 679394651928963067279918579724198 and fams[E.FRONT_VALUE_WEI]["name"] == "v2.433" and not fams[E.FRONT_VALUE_WEI]["dry_run"], fams
def refused(js):
    os.environ["FRONT_FAMILIES"] = js
    try:
        E.front_families(); return None
    except SystemExit as e:
        return str(e)
    finally:
        os.environ.pop("FRONT_FAMILIES", None)
base3 = json.loads(V3_JSON)[0]
for change, needle in ((("minout", 0.9), "unknown keys"), (("stake_wei", 10 ** 15), "unknown keys"), (("value_wei", None), "must give value_wei"), (("sqrt_p", None), "must give sqrt_p"),
                       (("value_wei", 3e18), "integer or a string of digits"), (("stake_eth", 0.05), "stake"), (("stake_eth", 0), "stake"), (("fee", 0), "fee 0"), (("bot_minout", 1.5), "bot_minout"),
                       (("hold_blocks", 0), "hold_blocks"), (("value_wei", str(E.FRONT_VALUE_WEI)), "two families launch with"), (("name", "v2.433"), "two families named"),
                       (("dry_run", "false"), "true or false"), (("hold_blocks", 1.9), "whole number"), (("fee", True), "must be a number"), (("ahead_max_eth", 0.001), "at least the stake"),
                       (("name", 5), "name must be"), (("fire_at", 149), "TRIGGER_MAX_BLOCKS"), (("take_profit", -1), "take_profit"), (("liq", "0"), "out of range"), (("sqrt_p", "1"), "sqrt_p"),
                       (("value_wei", "1" + "0" * 30), "value_wei"), (("sqrt_p", str(E.MAX_SQRT_P)), "sqrt_p"), (("name", "a b"), "name must be"), (("name", "x" * 65), "name must be")):
    f = dict(base3); k, v = change
    if v is None: f.pop(k)
    else: f[k] = v
    why = refused(json.dumps([f])); assert why and needle in why, (change, why)
assert "JSON list" in refused('{"a": 1}') and "not an object" in refused("[1]") and "fire_at" in refused(json.dumps([{**base3, "fire_at": -1}]))
assert "given twice" in refused('[{"name":"a","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"1","dry_run":true,"dry_run":false}]')
assert "not valid JSON" in refused('[{"name":"a",}]')
assert fams[3 * 10 ** 18]["fire_at"] == 0 and fams[3 * 10 ** 18]["fire_max"] == E.FRONT_FIRE_MAX
os.environ["FRONT_FAMILIES"] = "  "; assert set(E.front_families()) == {E.FRONT_VALUE_WEI}; os.environ.pop("FRONT_FAMILIES")
for stake, ok in ((0.0097, True), (0.012, True), (0.0121, False), (0.013, False)):                  # the stake cap is the 2.4333 bot's room (0.012 ETH), not the old 0.006
    os.environ["FRONT_FAMILIES"] = V3_JSON.replace('"stake_eth":0.002', f'"stake_eth":{stake}')
    try:
        got = E.front_families(E.front_base_family()); assert ok and got[3 * 10 ** 18]["stake_wei"] == int(round(stake * 1e9)) * 10 ** 9, (stake, got.get(3 * 10 ** 18, {}).get("stake_wei"))
    except SystemExit as e:
        assert not ok and "stake" in str(e), (stake, e)
os.environ.pop("FRONT_FAMILIES"); assert E.FRONT_STAKE_CAP_WEI == int(0.012e18) and E.FRONT_STAKE_CAP_ETH == 0.012
print("ok FRONT_FAMILIES: the runbook's JSON parses (stake, room, dry run, pin, fire offset per family); unknown keys, missing fingerprints, floats, a stake over the cap (0.012 ETH), fee 0, duplicates are refused at start")

# 19b. the pull check's block range on a provider whose node refuses a range past its head: it ends 10 under the head, never under the sell block
reset(); E.state["nonce"] = 6700; E.state["front_halted"] = None; E.state["armed"].pop(FPID, None); E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
rpc0 = E.rpc; asked = []; HEAD = [0]; BUMP = [0]
def head_rpc(method, params, tries=4, timeout=10):
    if method == "eth_blockNumber": return hex(HEAD[0])
    if method == "eth_getLogs":
        asked.append((int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)))
        if asked[-1][1] > HEAD[0]:
            HEAD[0] += BUMP[0]                                                                                     # a node that catches up between the tries
            raise RuntimeError("block range extends beyond current head block")
        return []
    return rpc0(method, params, tries, timeout)
E.rpc = head_rpc
#                                head  bump  to    asks  ok
for i, (head_rel, bump, want_to, asks, ok) in enumerate(((-3, 0, 0, 3, False), (-3, 4, 0, 2, True), (5, 0, 0, 1, True), (25, 0, 15, 1, True), (40, 0, 30, 1, True), (60, 0, 30, 1, True))):
    L = 8600 + 200 * i; front_launch(L, 27 + i); pos = E.state["position"]; assert pos and pos["entry"] == "front", (i, E.state["position"])
    E.ingest(frame(L + 1, [SENT[-1][1]]))
    for s_ in range(L + 2, L + 2 + E.FRONT_HOLD_BLOCKS):
        E.ingest(frame(s_, []))
    b1 = L + 1 + E.FRONT_HOLD_BLOCKS + 1; HEAD[0] = b1 + head_rel; BUMP[0] = bump; asked.clear(); alarms0 = len([e for e in events("alarm") if e["what"].startswith("pull check unreadable")])
    d = front_close(pos, L + 1, b1, int(E.FRONT_STAKE_WEI * 1.05))
    assert asked and asked[-1] == (L + 1, b1 + want_to), (head_rel, bump, asked)                                  # the range: our buy's block to min(sell + 30, head - 10), floor the sell block
    assert len(asked) == asks, (head_rel, bump, asked)                                                            # a refused range is asked again (a load-balanced node a few blocks behind), 3 times at most
    alarms = len([e for e in events("alarm") if e["what"].startswith("pull check unreadable")]) - alarms0
    if ok:
        assert d.get("pull_check_to") == want_to and d.get("pull_check") is None and d.get("pulled_before_sell") is False and alarms == 0, (head_rel, bump, d)
    else:
        assert "head" in (d.get("pull_check") or "") and d.get("pulled_before_sell") is None and "pull_check_to" not in d and alarms == 1, (head_rel, bump, d)   # a lagging head fails the check, never misses a pull
    assert d["pull_check_head"] == head_rel + bump * (asks - 1), d                                                # the head of the last try
    assert E.state["front_halted"] is None and not E.state["fam_halted"], (E.state["front_halted"], E.state["fam_halted"])
    E.state["armed"].pop(FPID, None)
E.rpc = rpc0; E.FRONT = False; E.ENTRY = "follow"; reset()
print("ok the pull check on a provider's node: the range ends 10 blocks under the head and never under the sell (a lagging head fails the check after 3 tries instead of missing a pull; a node that catches up passes)")

# 19c. the pull check's floor for follow: the near-miss halt needs the logs up to buy + FOLLOW_NEAR_MISS_BLOCKS (4) even past the sell block (buy + 3),
# so a head 2 blocks past the sell (head - 10 under every floor) still asks to buy + 4; a node answers only the range asked
reset(); E.state["armed"].pop(FPID, None); LOGS[:] = []
rpc0 = E.rpc; asked = []; HEAD = [0]
def head_rpc2(method, params, tries=4, timeout=10):
    if method == "eth_blockNumber": return hex(HEAD[0])
    if method == "eth_getLogs":
        lo, hi = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16); asked.append((lo, hi))
        if hi > HEAD[0]: raise RuntimeError("block range extends beyond current head block")
        return [l for l in LOGS if lo <= int(l["blockNumber"], 16) <= hi]
    return rpc0(method, params, tries, timeout)
E.rpc = head_rpc2
pos, buy_raw, B = relay_trade(8900, 640, 93)
E.ingest(frame(B + 1, [])); E.ingest(frame(B + 2, [])); assert pos["sell_sent"]
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(B, -E.STAKE_WEI, pos["feed_tokens"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(B + 3, int(E.STAKE_WEI * 0.995), -pos["feed_tokens"], index=2)
LOGS[:] = [{"blockNumber": hex(B + 4), "transactionIndex": hex(1), "data": "0x" + w(-887200) + w(TICK0) + w(-LIQ) + w(0)}]
HEAD[0] = B + 5
assert wait_for(lambda: done_at(640)); d = done_at(640)[-1]
assert asked == [(B, B + 4)], asked                                                                            # follow's floor: buy + 4, one past the sell block
assert d["pull_after_buy_blocks"] == 4 and d.get("near_miss") is True and d["pull_check_to"] == 1 and d["pull_check_head"] == 2 and d.get("fam") is None, d
assert E.state["follow_halted"] and E.state["follow_halted"].startswith("near miss") and E.state["front_halted"] is None, E.state["follow_halted"]
E.rpc = rpc0; LOGS[:] = []; E.state["follow_halted"] = None; os.remove(E.FOLLOW_HALT_FILE); E.load_halt(); assert E.state["follow_halted"] is None; reset()
print("ok the pull check's floor for follow: a head 2 past the sell still asks to buy + FOLLOW_NEAR_MISS_BLOCKS, so the near-miss halt is not missed")

# 20d. a family's fire offset: the delayed front fires when the feed shows launch + fire_at (after the operator's early-pull window, before its late bot buy),
# not in the launch block; too late past fire_at + fire_max; the bot's buy before the fire still makes the pool late
E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"; reset(); E.state["nonce"] = 760; E.state["front_halted"] = None
E.FRONT_FAMILIES[V3_VALUE] = {**FAM0, "name": "v3", "value_wei": V3_VALUE, "fee": 10000, "tick_spacing": 200, "sqrt_p": V3_SQRT, "liq": V3_LIQ, "bot_minout": 0.95, "ahead_max_wei": int(0.07e18),
                               "take_profit": 9.0, "hold_blocks": 60, "stake_wei": int(0.002e18), "dry_run": False, "pin": False, "fire_at": 12, "fire_max": 2}
E.state["delayed"] = True; n_sent = len(SENT); E.ingest(frame(9900, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 3)]))
p3 = E.state["armed"].get(d3["pid"]); assert p3 and p3["status"] == "armed" and E.state["position"] is None and len(SENT) == n_sent, "fired in the launch block despite fire_at 12"
for s_ in range(9901, 9912):
    E.ingest(frame(s_, [])); assert E.state["position"] is None and p3["status"] == "armed", s_
E.ingest(frame(9912, [])); pos = E.state["position"]; assert pos and pos["fam"] == "v3" and pos["fire_seq"] == 9912 and pos["trig_seq"] == 9912 and p3["launch_seq"] == 9900 and len(SENT) == n_sent + 1 and pos["send_after"] == 60, pos
E.ingest(frame(9913, [SENT[-1][1]])); assert pos["buy_seq"] == 9913
for s_ in range(9914, 9940):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(9940, [signed(CROWD, BOT, int(0.12e18), FBUY, 85)]))                      # the bot's late buy at launch + 40: the exit
assert pos["sell_sent"] and pos.get("bot_exit") and pos["sell_why"].startswith("the bot's buy behind ours"), pos.get("sell_why")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(9913, -int(0.002e18), pos["feed_tokens"], pid=d3["pid"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(9941, int(0.002e18 * 1.06), -pos["feed_tokens"], pid=d3["pid"])
assert wait_for(lambda: done_at(760)); assert done_at(760)[-1]["fam"] == "v3" and done_at(760)[-1]["ret"] > 0.04, done_at(760)[-1]
reset(); E.state["nonce"] = 770; E.state["armed"].clear()                                # too late: the feed shows launch + 15 first (a stall): no fire
E.ingest(frame(9950, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 4)])); p3 = E.state["armed"][d3["pid"]]
E.ingest(frame(9965, [])); assert E.state["position"] is None and p3["status"] == "late" and events("skip")[-1]["why"].startswith("front: too late"), events("skip")[-1]
reset(); E.state["nonce"] = 780; E.state["armed"].clear()                                # the bot's buy before our fire offset: late, no fire
E.ingest(frame(9970, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 5)])); p3 = E.state["armed"][d3["pid"]]
E.ingest(frame(9975, [signed(CROWD, BOT, int(0.12e18), FBUY, 86)])); assert p3["status"] == "late" and E.state["position"] is None
for s_ in range(9976, 9984):
    E.ingest(frame(s_, []))
assert E.state["position"] is None, "fired after the bot's buy"
reset(); E.state["nonce"] = 790; E.state["armed"].clear()                                # the operator's pull before our fire offset (a value-0 call on its router carrying the token): late, no fire
E.ingest(frame(9990, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 6)])); p3 = E.state["armed"][d3["pid"]]
E.ingest(frame(9998, [signed(DEPLOYER, BOT, 0, "0xa0f7978d" + w(FTOKEN) + w(0) * 3, 7)])); assert p3["status"] == "late" and "pull" in events("skip")[-1]["why"], events("skip")[-1]
for s_ in range(9999, 10004):
    E.ingest(frame(s_, []))
assert E.state["position"] is None, "fired into a pulled pool"
E.state["delayed"] = False
# 20e. a listed family's pull-first halt halts that family alone (its own file): the FRONT_* line goes on; the file is read back at a start
reset(); E.state["nonce"] = 800; E.state["armed"].clear(); E.state["front_halted"] = None; E.FRONT_FAMILIES[V3_VALUE]["fire_at"] = 0; E.FRONT_FAMILIES[V3_VALUE]["hold_blocks"] = 20
E.ingest(frame(10100, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 8)])); pos = E.state["position"]; assert pos and pos["fam"] == "v3"
E.ingest(frame(10101, [SENT[-1][1]])); assert pos["buy_seq"] == 10101
for s_ in range(10102, 10102 + 20):
    E.ingest(frame(s_, []))
assert pos["sell_sent"] and pos["sell_why"].startswith("deadline")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(10101, -int(0.002e18), pos["feed_tokens"], pid=d3["pid"]); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(10123, 0, 0, pid=d3["pid"])
LOGS_PULL = [{"blockNumber": hex(10110), "transactionIndex": "0x1", "data": "0x" + w(0) * 2 + w((2 ** 256) - 10 ** 20) + w(0), "topics": ["0x" + "11" * 32, d3["pid"]]}]
rpc0 = E.rpc
def rpc_pull(method, params, tries=4, timeout=10):
    if method == "eth_getLogs": return LOGS_PULL
    return rpc0(method, params, tries, timeout)
E.rpc = rpc_pull
assert wait_for(lambda: done_at(800)); d = done_at(800)[-1]; E.rpc = rpc0
assert d["pulled_before_sell"] is True and E.state["fam_halted"].get("v3") and E.state["front_halted"] is None and E.state["halted"] is None, (d.get("pulled_before_sell"), E.state["fam_halted"], E.state["front_halted"])
assert d["fam"] == "v3" and d["entry"] == "front", d                                                             # the trade's record names its family (results and checks filter on it)
assert os.path.exists(E.fam_halt_file("v3")) and not os.path.exists(E.FRONT_HALT_FILE)
E.state["armed"].clear(); assert E.state["position"] is None and E.state["front_settling"] is None, "the settle must free the slot"
E.ingest(frame(10200, [signed(DEPLOYER, POSM, V3_VALUE, "0x" + relaunch(10000, 200, V3_SQRT, V3_LIQ).hex(), 9)]))
assert E.state["position"] is None and "halted" in events("skip")[-1]["why"], events("skip")[-1]                                       # the halted family does not fire
E.state["nonce"] = 810; E.state["front_pnl_today_usd"] = 0.0; front_launch(10300, 10); assert E.state["position"] and E.state["position"]["fam"] == "v2.433", ("the FRONT_* line must go on", events("skip")[-1])   # the base family does
E.state["fam_halted"].clear(); E.load_halt(); assert E.state["fam_halted"].get("v3"), "the family's halt file was not read back"
os.remove(E.fam_halt_file("v3")); E.state["fam_halted"].clear(); del E.FRONT_FAMILIES[V3_VALUE]; reset(); E.FRONT = False; E.ENTRY = "follow"
print("ok a listed family's pull-first halt halts that family alone (its own file, read back at a start); the FRONT_* line goes on")
print("ok a family's fire offset: the delayed front fires at launch + fire_at, holds for the bot's late buy, is late past fire_at + fire_max or once the bot has bought")
# --- 20f. a wave family (C-1): the launch (PositionManager multicall of 2,276 bytes, value 0, a token-only range up to the launch tick) arms and
# waits; the operator's buy through its router (a value-0 call carrying the token and the buy flag) is the trigger: we buy behind it (landing + 2)
# and sell hold_blocks later; a pull-shaped call before the trigger, a trigger past the family's window, or no trigger make the pool late; a dry
# family scores its would-be sell (dry_ret)
C1 = json.load(open(os.path.join(ROOT, "tests", "data", "c1_launch.json")))
C1_ROUTER = C1["router_to"]; C1_PID = C1["pid"]; C1_TOKEN = C1["token"]; C1_BUY = C1["router_input"]
C1_SELL = C1_BUY[:10 + 64 * 7] + w(1) + C1_BUY[10 + 64 * 8:]                                                 # the same call with the action flag 1: the router's sell
assert C1_BUY[10 + 64 * 8 + 24: 10 + 64 * 9] == C1_TOKEN[2:].lower() and int(C1_BUY[10 + 64 * 2: 10 + 64 * 3], 16) == C1["router_q_wei"] and int(C1_BUY[10 + 64 * 7: 10 + 64 * 8], 16) == 0
C1_FAM = {"name": "c1", "value_wei": 0, "calldata_len": 2276, "fee": 100, "tick_spacing": 1, "sqrt_p": str(C1["sqrt_p"]), "liq": str(C1["liq"]), "bot_minout": 1.0, "ahead_max_eth": 0.5,
          "take_profit": 9, "hold_blocks": 60, "stake_eth": 0.0058, "dry_run": False, "pin": True,
          "trigger": {"router": C1_ROUTER, "selector": "e6cb474f", "value_word": 2, "token_word": 8, "flag_word": 7, "flag_value": 0, "min_eth": 0.005, "max_blocks": 400}}
os.environ["FRONT_FAMILIES"] = json.dumps([C1_FAM]); fams = E.front_families(E.front_base_family()); os.environ.pop("FRONT_FAMILIES")
c1 = fams[0]; assert c1["name"] == "c1" and c1["calldata_len"] == 2276 and c1["trigger"]["router"] == C1_ROUTER[2:].lower() and c1["trigger"]["selector"] == "e6cb474f" and c1["trigger"]["words"] == 9 \
    and c1["trigger"]["min_wei"] == int(0.005e18) and c1["trigger"]["max_blocks"] == 400 and c1["trigger"]["flag_word"] == 7 and c1["fire_at"] == 0 and c1["liq"] == C1["liq"], c1
for patch, msg in (({"trigger": None}, "needs a trigger"), ({"fire_at": 5}, "fire_at must be 0"), ({"trigger": {"router": C1_ROUTER}}, "selector"),
                   ({"trigger": {"router": "0x12", "selector": "e6cb474f", "flag_word": 7}}, "40 hex"), ({"trigger": {"router": C1_ROUTER, "selector": "e6cb474f", "flag_word": 7, "nope": 1}}, "unknown keys"),
                   ({"calldata_len": 20}, "calldata_len"), ({"trigger": {"router": C1_ROUTER, "selector": "e6cb474f", "flag_word": 7, "max_blocks": 5000}}, "max_blocks"),
                   ({"trigger": {"router": C1_ROUTER, "selector": "e6cb474f", "flag_word": 7, "min_eth": 0}}, "min_eth"), ({"trigger": "0xd6d35b56"}, "must be an object"), ({"calldata_len": 1444.5}, "whole number"),
                   ({"trigger": {"router": C1_ROUTER, "selector": "e6cb474f"}}, "flag_word"), ({"trigger": {**C1_FAM["trigger"], "max_blocks": 2000}, "hold_blocks": 601}, "hold_blocks"),
                   ({"trigger": {**C1_FAM["trigger"], "max_blocks": 2000}, "hold_blocks": 600}, "under 2600"), ({"trigger": {**C1_FAM["trigger"], "max_eth": 0}}, "max_eth"),
                   ({"trigger": {**C1_FAM["trigger"], "max_eth": 0.004}}, "at least min_eth")):
    os.environ["FRONT_FAMILIES"] = json.dumps([{**C1_FAM, **patch}])
    try:
        E.front_families(E.front_base_family()); assert False, ("accepted", patch)
    except SystemExit as e:
        assert msg in str(e), (patch, str(e))
os.environ.pop("FRONT_FAMILIES")
E.FRONT_FAMILIES[0] = c1; E.WAVE_ROUTERS.add(c1["trigger"]["router"]); E.state["delayed"] = True; E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"
reset(); E.state["nonce"] = 900; E.state["front_halted"] = None; E.state["fam_halted"].clear(); LOGS[:] = []
n_sent = len(SENT); E.ingest(frame(12000, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 10)]))
p = E.state["armed"].get(C1_PID); assert p and p["entry"] == "front" and p["fam"] == "c1" and p["eligible"] and p["liq"] == C1["liq"] and p["tick0"] == C1["hi"] and p["status"] == "armed" \
    and E.state["position"] is None and len(SENT) == n_sent, (p and {k: p[k] for k in ("eligible", "liq", "status", "tick0")}, events("armed")[-1].get("why"))
assert events("launch")[-1]["fam"] == "c1" and events("armed")[-1]["fingerprint"] == "known"
for s_ in range(12001, 12100):
    E.ingest(frame(s_, []))
assert E.state["position"] is None and p["status"] == "armed", "fired without a trigger"
E.ingest(frame(12100, [signed(OUTSIDER, UR, int(0.0003e18), "0x12345678" + w(C1_TOKEN), 50)]))         # a stranger's small buy with ETH: the price copy moves, nothing fires
assert E.state["position"] is None and p["status"] == "armed" and p["buys"] == 1 and p["eth_in"] == int(0.0003e18) and p["first_buy"] is None, (p["status"], p["buys"], p["first_buy"])
E.ingest(frame(12110, [signed(CROWD, C1_ROUTER, 0, C1_SELL, 51)]))                                      # the router's sell-shaped call: not a buy, no trigger
assert E.state["position"] is None and p["first_buy"] is None and p["buys"] == 1, "the router's sell was taken for a buy"
C1_HUGE = C1_BUY[:10 + 64 * 2] + w(2 ** 200) + C1_BUY[10 + 64 * 3:]                                      # a forged or reverting call with an absurd amount: ignored
E.ingest(frame(12111, [signed(CROWD, C1_ROUTER, 0, C1_HUGE, 60)]))
assert E.state["position"] is None and p["first_buy"] is None and p["buys"] == 1 and events("skip")[-1]["why"].startswith("wave: a router call with an absurd amount"), events("skip")[-1]
E.ingest(frame(12112, [signed(DEPLOYER, POSM, 0, "0xac9650d8" + "00" * 2240 + w(C1_TOKEN), 61)]))      # a value-0 PositionManager call of the family's length that is no launch but carries the pool's token (a pull shape):
assert events("launch_undecoded")[-1]["fam"] == "c1" and len(E.state["armed"]) == 1                              # logged, not armed, and the pull scan still ran: the pool is late
assert p["status"] == "late" and "pull" in events("skip")[-1]["why"], (p["status"], events("skip")[-1])
reset(); E.state["nonce"] = 905; E.state["armed"].clear(); LOGS[:] = []                                           # a fresh launch for the trigger path below
n_sent = len(SENT); E.ingest(frame(12120, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 16)])); p = E.state["armed"][C1_PID]
E.ingest(frame(12121, [signed(OUTSIDER, UR, int(0.0003e18), "0x12345678" + w(C1_TOKEN), 62)])); assert p["buys"] == 1
sp_before = p["sp"]; E.ingest(frame(12150, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 52)]))                  # the operator's buy: the trigger
pos = E.state["position"]; assert pos and pos["fam"] == "c1" and pos["entry"] == "front" and pos["trig_seq"] == 12150 and pos["fire_seq"] == 12150 and pos["plan_buy_seq"] == 12152 \
    and pos["send_after"] == 60 and pos["stake"] == int(0.0058e18) and pos["trig_value"] == C1["router_q_wei"] and len(SENT) == n_sent + 1 and p["first_buy"] == 12150 and p["sp"] < sp_before, pos
assert events("first_buy")[-1].get("trigger") is True and events("first_buy")[-1]["value"] == C1["router_q_wei"] and events("first_buy")[-1]["offset"] == 30
E.ingest(frame(12152, [SENT[-1][1]])); assert pos["buy_seq"] == 12152 and pos["feed_tokens"] > 0
E.ingest(frame(12160, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 53)]))                                       # a second operator buy behind ours: the price copy moves, take-profit (9) does not fire
assert not pos["sell_sent"] and p["buys"] == 4, (pos["sell_sent"], p["buys"])                            # the stranger's, the trigger, our own, the operator's second
for s_ in range(12161, 12212):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(12212, [])); assert pos["sell_sent"] and pos["sell_why"].startswith("deadline"), pos.get("sell_why")
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(12152, -int(0.0058e18), pos["feed_tokens"], pid=C1_PID); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(12213, int(0.0058e18 * 1.1), -pos["feed_tokens"], pid=C1_PID)
assert wait_for(lambda: done_at(905)); d = done_at(905)[-1]; assert d["fam"] == "c1" and d["entry"] == "front" and d["ret"] > 0.08 and d["hold_blocks"] == 61 and d["buy_offset"] == 2 and not d.get("pulled_before_sell"), d
assert E.state["front_halted"] is None and not E.state["fam_halted"] and E.state["position"] is None
reset(); E.state["nonce"] = 910; E.state["armed"].clear()                                                # no trigger within the window: late, nothing fires
E.ingest(frame(12300, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 11)])); p2 = E.state["armed"][C1_PID]
for s_ in range(12301, 12701):
    E.ingest(frame(s_, []))
assert p2["status"] == "armed", "late before the window's end"
E.ingest(frame(12701, [])); assert p2["status"] == "late" and events("skip")[-1]["why"].startswith("wave: no trigger within") and E.state["position"] is None, events("skip")[-1]
E.ingest(frame(12702, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 54)])); assert E.state["position"] is None, "fired after the window"
reset(); E.state["nonce"] = 920; E.state["armed"].clear()                                                # a pull-shaped call on the pool before the trigger: late
E.ingest(frame(12800, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 12)])); p3 = E.state["armed"][C1_PID]
E.ingest(frame(12805, [signed(DEPLOYER, POSM, 0, "0xdd46508f" + w(C1_TOKEN) + w(0) * 3, 13)])); assert p3["status"] == "late" and "pull" in events("skip")[-1]["why"], events("skip")[-1]
E.ingest(frame(12810, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 55)])); assert E.state["position"] is None, "fired after a pull"
reset(); E.state["nonce"] = 930; E.state["armed"].clear()                                                # the trigger itself past the window (a stall): late
E.ingest(frame(13000, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 14)])); p4 = E.state["armed"][C1_PID]
E.ingest(frame(13401, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 56)])); assert E.state["position"] is None and p4["status"] == "late" and "window" in events("skip")[-1]["why"], events("skip")[-1]
reset(); E.state["nonce"] = 940; E.state["armed"].clear(); E.FRONT_FAMILIES[0] = {**c1, "dry_run": True}   # the dry family: would_fire, the virtual buy, would_sell with its return
n_sent = len(SENT); E.ingest(frame(13500, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 15)])); p5 = E.state["armed"][C1_PID]
E.ingest(frame(13520, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 57)])); pos = E.state["position"]
assert pos and pos["dry"] and pos["fam"] == "c1" and events("would_fire")[-1]["fam"] == "c1" and events("would_fire")[-1]["plan_buy_seq"] == 13522 and len(SENT) == n_sent, pos
E.ingest(frame(13521, [])); E.ingest(frame(13522, [])); assert pos["buy_seq"] == 13522 and pos["feed_tokens"] > 0, "the dry run's buy did not land at its planned block"
E.ingest(frame(13530, [signed(CROWD, C1_ROUTER, 0, C1_BUY, 58)]))                                        # the operator buys again behind us
for s_ in range(13531, 13583):
    E.ingest(frame(s_, []))
assert pos["sell_sent"] and events("would_sell")[-1]["dry_ret"] is not None and -0.02 < events("would_sell")[-1]["dry_ret"] < 0.5, events("would_sell")[-1]
assert wait_for(lambda: any(e.get("dry") and e.get("fam") == "c1" and "dry_ret" in e for e in events("trade_done")), 3.0), "no dry trade_done with dry_ret"
del E.FRONT_FAMILIES[0]; E.WAVE_ROUTERS.discard(c1["trigger"]["router"]); E.state["delayed"] = any(f["fire_at"] or f["trigger"] for f in E.FRONT_FAMILIES.values()); reset(); E.FRONT = False; E.ENTRY = "follow"
print("ok a wave family (C-1): the value-0 launch arms with its one-sided liquidity and waits; the operator's router buy is the trigger (buy + 2, sell at the hold); the router's sell, a stranger's buy, a pull before the trigger and the window's end never fire; the dry family scores its sell")

# --- 20h. known fingerprints and the auto stake: a family accepts the fees / tick spacings it is known to use (the 2.4333 line's 2500/50 and
# 5000/100 of Oct 11) and refuses the rest; FRONT_AUTO_STAKE sizes the stake to the room the bot's decoys leave, measured at each bot buy
E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"; reset(); E.state["nonce"] = 1000; E.state["front_halted"] = None; E.state["armed"].clear()
base = E.FRONT_FAMILIES[E.FRONT_VALUE_WEI]; saved = {k: base.get(k) for k in ("fees_also", "tick_spacings_also", "stake_wei", "ahead_max_wei")}
base["fees_also"] = [5000]; base["tick_spacings_also"] = [100]
E.state["position"] = {"pid": "0x" + "00" * 32, "dry": False, "buy_hash": None, "buy_seq": 1, "sell_sent": True, "plan_buy_seq": 0, "send_after": 0, "feed_tokens": None, "entry": "front"}   # the slot held: launches arm, none fires
front_launch(14000, 100); p = E.state["armed"][FPID]; assert p["eligible"] and events("armed")[-1]["fingerprint"] == "known", events("armed")[-1]       # the line's own 2500/50
E.state["armed"].clear(); E.ingest(frame(14010, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, "0x" + relaunch(5000, 100, FX["sqrt_p"], FX["liq"]).hex(), 101)]))
p = [q for q in E.state["armed"].values()][-1]; assert p["fee"] == 5000 and p["tick_spacing"] == 100 and p["eligible"] and events("armed")[-1]["fingerprint"] == "known", events("armed")[-1]   # the Oct 11 pair
E.state["armed"].clear(); E.ingest(frame(14020, [signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, "0x" + relaunch(3000, 60, FX["sqrt_p"], FX["liq"]).hex(), 102)]))
assert not E.state["armed"] and events("armed")[-1]["why"] == "front: fee 3000", events("armed")[-1]                                                  # an unseen pair is still refused
for patch, msg in (({"fees_also": [0]}, "fees_also"), ({"fees_also": list(range(1, 10))}, "fees_also"), ({"fees_also": "5000"}, "fees_also"), ({"tick_spacings_also": [True]}, "tick_spacings_also"), ({"tick_spacings_also": [40000]}, "tick_spacings_also")):
    os.environ["FRONT_FAMILIES"] = V3_JSON[:-2] + "," + json.dumps(patch)[1:-1] + "}]"
    try:
        E.front_families(E.front_base_family()); assert False, ("accepted", patch)
    except SystemExit as e:
        assert msg in str(e), (patch, str(e))
os.environ["FRONT_FAMILIES"] = V3_JSON[:-2] + ',"fees_also":[5000,2500],"tick_spacings_also":[50]}]'; fams = E.front_families(E.front_base_family()); os.environ.pop("FRONT_FAMILIES")
assert fams[3 * 10 ** 18]["fees_also"] == [2500, 5000] and fams[3 * 10 ** 18]["tick_spacings_also"] == [50], fams[3 * 10 ** 18]
# the auto stake
E.FRONT_AUTO_STAKE = True; E.FRONT_AUTO_STAKE_WINDOW = 8; E.state["room_obs"] = {}; base["stake_wei"] = int(0.0097e18); base["ahead_max_wei"] = int(0.0115e18)
assert E.auto_stake(base) == int(0.002e18) and E.fam_stake(base) == int(0.002e18), "no observations: the minimum"
DUST = lambda n: signed(OUTSIDER, UR, int(0.00495e18), "0x12345678" + w(FTOKEN), n)
for i in range(6):                                                                                   # six pools where the decoys took 0.0099 ETH before the bot's buy
    L = 14100 + 50 * i; E.state["armed"].clear(); front_launch(L, 110 + i); p = E.state["armed"][FPID]
    E.ingest(frame(L + 1, [DUST(200 + 2 * i), signed(CROWD, UR, int(0.00495e18), "0x12345678" + w(FTOKEN), 201 + 2 * i)])); assert p["eth_in"] == int(0.0099e18)
    E.ingest(frame(L + 9, [signed(CROWD, BOT, int(0.15e18), FBUY, 300 + i)]))
    r = events("room")[-1]; assert r["fam"] == "v2.433" and r["obs"] == i + 1 and abs(r["ahead_eth"] - 0.0099) < 1e-9 and 0.0022 < r["room_eth"] < 0.0030, r   # the room (~0.0126 at this fee) less the decoys
    obs = sorted(E.state["room_obs"]["v2.433"]); exp = max(int(0.002e18), min(base["stake_wei"], (obs[int(len(obs) * 0.25)] - int(0.0004e18)) // 10 ** 14 * 10 ** 14))
    assert E.auto_stake(base) == (int(0.002e18) if i + 1 < E.FRONT_AUTO_STAKE_OBS else exp) and int(0.0021e18) <= exp <= int(0.0026e18), (i, E.auto_stake(base), exp)   # the 25th percentile less the margin, to 0.0001
want = E.auto_stake(base); E.state["position"] = None; E.state["armed"].clear(); n_sent = len(SENT); front_launch(14500, 120); pos = E.state["position"]
assert pos and pos["stake"] == want and len(SENT) == n_sent + 1, (pos and pos["stake"], want)
bf = rlp.decode(SENT[-1][1]); assert bf[5].hex()[8 + 64 * 5: 8 + 64 * 6] == w(want), "the buy's amountIn is the auto stake"
E.state["position"] = {"pid": "0x" + "00" * 32, "dry": False, "buy_hash": None, "buy_seq": 1, "sell_sent": True, "plan_buy_seq": 0, "send_after": 0, "feed_tokens": None, "entry": "front"}
for i in range(8):                                                                                   # eight clean pools: the room is the whole 0.0124, the stake climbs to the family's ceiling
    L = 14600 + 50 * i; E.state["armed"].clear(); front_launch(L, 130 + i); E.ingest(frame(L + 9, [signed(CROWD, BOT, int(0.15e18), FBUY, 320 + i)]))
r = events("room")[-1]; assert r["ahead_eth"] == 0 and 0.0120 < r["room_eth"] < 0.0128 and r["obs"] == 8, r
assert E.auto_stake(base) == int(0.0097e18), E.auto_stake(base)
E.state["position"] = None; E.state["armed"].clear(); front_launch(15100, 140); pos = E.state["position"]; assert pos["stake"] == int(0.0097e18), pos["stake"]
E.ingest(frame(15101, [SENT[-1][1]])); assert pos["buy_seq"] == 15101
for s_ in range(15102, 15102 + E.FRONT_HOLD_BLOCKS):
    E.ingest(frame(s_, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(15101, -int(0.0097e18), pos["feed_tokens"], pid=FPID); RECEIPTS["0x" + pos["sell_hash"]] = swap_receipt(15120, int(0.0097e18 * 0.99), -pos["feed_tokens"], pid=FPID)
assert wait_for(lambda: done_at(pos["nonce"])); d = done_at(pos["nonce"])[-1]
assert d.get("room_obs_reset") is True and "v2.433" not in E.state["room_obs"] and E.auto_stake(base) == int(0.002e18), (d.get("room_obs_reset"), E.auto_stake(base))   # a raised stake that did not pay: back to the floor
E.state["front_nonbot_streak"] = {}; E.state["position"] = {"pid": "0x" + "00" * 32, "dry": False, "buy_hash": None, "buy_seq": 1, "sell_sent": True, "plan_buy_seq": 0, "send_after": 0, "feed_tokens": None, "entry": "front"}
for i in range(8):                                                                                   # eight clean pools again, then one decoyed one: the stake comes down at once
    L = 15200 + 50 * i; E.state["armed"].clear(); front_launch(L, 150 + i); E.ingest(frame(L + 9, [signed(CROWD, BOT, int(0.15e18), FBUY, 340 + i)]))
assert E.auto_stake(base) == int(0.0097e18)
E.state["armed"].clear(); front_launch(15700, 160); p = E.state["armed"][FPID]; E.ingest(frame(15701, [DUST(360), signed(CROWD, UR, int(0.00495e18), "0x12345678" + w(FTOKEN), 361)])); E.ingest(frame(15709, [signed(CROWD, BOT, int(0.15e18), FBUY, 362)]))
assert int(0.0021e18) <= E.auto_stake(base) <= int(0.0026e18), E.auto_stake(base)                      # one decoyed pool among the last five caps the percentile
E.FRONT_AUTO_STAKE = False; assert E.fam_stake(base) == int(0.0097e18), "auto stake off: the family's stake"
base.update(saved); E.state["room_obs"] = {}; E.state["position"] = None; reset(); E.FRONT = False; E.ENTRY = "follow"
print("ok known fingerprints (fees_also, tick_spacings_also) arm, an unseen fee is refused; the auto stake measures the room at each bot buy and sizes the stake from the minimum to the family's ceiling")
# --- 20g. a V3 family (the V3 crowd line, HANDOFF 16.16): its launch (a V3 PositionManager multicall of 836 bytes, value 0) decoded from the
# calldata (the pool's address by CREATE2, the price on the top tick of a token-only range) and armed; a dry fire in the launch block (landing
# + 2); the crowd's buys (value-0 calls of its shapes through any contract, the token at the end of a V3 path) move the price copy, and its
# first buy behind ours starts the exit's clock (the sell exit_after_blocks later), the cap at launch + hold_blocks; it never sends; C-1 (also
# value 0) and the 2.4333 line in the same run as before
import subprocess
V3 = json.load(open(os.path.join(ROOT, "tests", "data", "v3_launch.json"))); V3_NPM = V3["launch_to"]; V3_PID = V3["pool"]; V3_IN = V3["launch_input"]
B1, B2 = V3["buys"]; assert (B1["selector"], B1["calldata_len"], B2["selector"], B2["calldata_len"]) == ("3593564c", 484, "a0193551", 452)
d = E.decode_launch_v3(bytes.fromhex(V3_IN[2:]))
assert d["pid"] == V3_PID and "0x" + d["c0"] == V3["token0"] == "0x" + E.WETH and "0x" + d["token"] == V3["token"] and d["fee"] == 100 and d["tick_spacing"] == 1 and d["sqrt_p"] == V3["sqrt_p"] \
    and (d["lo"], d["hi"], d["tick0"]) == (V3["lo"], V3["hi"], V3["hi"]) and d["mint_liq"] == V3["liq"] and (d["amount0"], d["amount1"]) == (0, V3["amount1"]), d   # the chain's PoolCreated, Initialize, Mint
assert E.sqrt_at_tick(V3["hi"]) == V3["sqrt_p"] and E.sqrt_at_tick(E.V3_MIN_TICK) == E.MIN_SQRT_P and E.decode_launch_v3(bytes.fromhex(V3_IN[2:])[:600]) is None
assert E.decode_launch_v3(FIN) is None and E.decode_launch(bytes.fromhex(V3_IN[2:])) is None                     # neither decoder takes the other's launch
fs = V3["first_swap"]; got = v4math.buy_out_int(V3["sqrt_p"], V3["liq"], fs["weth_in"], 100); assert abs(got - fs["tokens_out"]) < fs["tokens_out"] * 1e-15, (got, fs)   # the pool's first real buy (+ 1), from the launch state
V3_FAM = {"name": "v3crowd", "dex": "v3", "target": V3_NPM, "value_wei": 0, "calldata_len": 836, "fee": 100, "tick_spacing": 1, "hold_blocks": 78, "exit_after_blocks": 18,
          "take_profit": 9, "stake_eth": 0.0058, "ahead_max_eth": 0.5, "dry_run": True, "pin": True,
          "trigger": {"shapes": [{"selector": "3593564c", "calldata_len": 484, "value_word": 9}, {"selector": "a0193551", "calldata_len": 452, "value_word": 8},
                                 {"selector": "49f74a5d", "calldata_len": 452, "value_word": 8}], "any_to": True, "token_anywhere": True, "min_eth": 0.005, "max_eth": 10}}
os.environ["FRONT_FAMILIES"] = json.dumps([C1_FAM, V3_FAM]); fams = E.front_families(E.front_base_family()); os.environ.pop("FRONT_FAMILIES")
K3 = ("v3", V3_NPM[2:]); v3f = fams[K3]; t3 = v3f["trigger"]
assert set(fams) == {E.FRONT_VALUE_WEI, 0, K3} and fams[0]["name"] == "c1" and v3f["dex"] == "v3" and fams[0]["dex"] == "v4", fams.keys()   # C-1 and the V3 line both launch with 0 ETH
assert v3f["target"] == V3_NPM[2:] and (v3f["exit_after_blocks"], v3f["hold_blocks"], v3f["calldata_len"], v3f["sqrt_p"], v3f["liq"]) == (18, 78, 836, 0, 0) and v3f["dry_run"] \
    and t3["router"] is None and t3["token_word"] is None and t3["flag_word"] is None and t3["shapes"] == {("3593564c", 484): 9, ("a0193551", 452): 8, ("49f74a5d", 452): 8} \
    and t3["min_wei"] == int(0.005e18) and E.trigger_desc(t3) == "any:3593564c/484,49f74a5d/452,a0193551/452" and E.trigger_desc(fams[0]["trigger"]) == C1_ROUTER[2:].lower() + ":e6cb474f", v3f
T3 = V3_FAM["trigger"]
for patch, msg in (({"dex": "v2"}, "dex must be"), ({"dry_run": False}, "not built"), ({"dry_run": None}, "not built"), ({"target": None}, "must give target"), ({"target": "0x1234"}, "40 hex"),
                   ({"target": E.POSITION_MANAGER}, "v4's PositionManager"), ({"exit_after_blocks": None}, "must give exit_after_blocks"), ({"exit_after_blocks": 0}, "exit_after_blocks"),
                   ({"calldata_len": None}, "must give calldata_len"), ({"hold_blocks": None}, "must give hold_blocks"), ({"trigger": None}, "must give trigger"), ({"fire_at": 2}, "fire_at 0"), ({"hold_blocks": 4}, "fire_max + 3"),
                   ({"sqrt_p": "1"}, "sqrt_p"), ({"trigger": {**T3, "shapes": "3593564c"}}, "list of 1-8"), ({"trigger": {**T3, "shapes": []}}, "list of 1-8"),
                   ({"trigger": {**T3, "shapes": [{"selector": "3593564c", "calldata_len": 484}]}}, "must give exactly"),
                   ({"trigger": {**T3, "shapes": [{"selector": "3593564c", "calldata_len": 484, "value_word": 9, "to": 1}]}}, "must give exactly"),
                   ({"trigger": {**T3, "shapes": [{"selector": "3593564", "calldata_len": 484, "value_word": 9}]}}, "8 hex"),
                   ({"trigger": {**T3, "shapes": [{"selector": "3593564c", "calldata_len": 300, "value_word": 9}]}}, "shorter than"),
                   ({"trigger": {**T3, "shapes": T3["shapes"] + T3["shapes"][:1]}}, "given twice"), ({"trigger": {**T3, "router": C1_ROUTER}}, "router or any_to"),
                   ({"trigger": {**T3, "any_to": False}}, "router or any_to"), ({"trigger": {**T3, "any_to": "yes"}}, "true or false"), ({"trigger": {**T3, "selector": "3593564c"}}, "or shapes"),
                   ({"trigger": {**T3, "token_word": 8}}, "not both"), ({"trigger": {**T3, "token_anywhere": False}}, "flag_word")):
    f = {**V3_FAM, **patch}; f = {k: v for k, v in f.items() if v is not None}
    why = refused(json.dumps([f])); assert why and msg in why, (patch, why)
os.environ["FRONT_FAMILIES"] = json.dumps([{k: v for k, v in V3_FAM.items() if k != "take_profit"}]); assert E.front_families()[K3]["take_profit"] == 9.0; os.environ.pop("FRONT_FAMILIES")   # off unless given
assert "for a V3 family" in refused(json.dumps([{**base3, "exit_after_blocks": 20}])) and "for a V3 family" in refused(json.dumps([{**base3, "target": V3_NPM}]))
assert "two V3 families" in refused(json.dumps([V3_FAM, {**V3_FAM, "name": "w2"}])) and "two families named" in refused(json.dumps([V3_FAM, {**V3_FAM, "target": "0x" + "ab" * 20}]))
def imported(js):
    """FRONT_FAMILIES at a real import (the service's start): the error and the families' keys"""
    r = subprocess.run([sys.executable, "-c", "import flip_engine as E, json; print(json.dumps([E.FRONT_FAMILY_ERROR, sorted(map(str, E.FRONT_FAMILIES))]))"], cwd=os.path.join(ROOT, "src"),
                       env={**os.environ, "FRONT_FAMILIES": js, "LOG_PATH": LOG + ".import"}, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-400:]; return json.loads(r.stdout.strip().splitlines()[-1])
for js in (json.dumps([{**V3_FAM, "dry_run": False}]), json.dumps([{**V3_FAM, "trigger": {**T3, "shapes": [[]]}}]), json.dumps([{**V3_FAM, "trigger": {**T3, "shapes": [{**T3["shapes"][0], "calldata_len": 1e400}]}}]), "[" * 10000 + "]" * 10000):
    err, keys = imported(js); assert err and err.startswith("FRONT_FAMILIES dropped, the FRONT_* line alone trades") and keys == [str(E.FRONT_VALUE_WEI)], (js[:80], err, keys)   # never a crash
err, keys = imported(json.dumps([C1_FAM, V3_FAM])); assert err is None and keys == sorted(map(str, [E.FRONT_VALUE_WEI, 0, K3])), (err, keys)
RB = next(l.strip()[len("FRONT_FAMILIES='"):-1] for l in open(os.path.join(ROOT, "docs", "RUNBOOK.md")) if l.strip().startswith("FRONT_FAMILIES='") and "v3crowd" in l)
err, keys = imported(RB); assert json.loads(RB)[2] == V3_FAM and err is None and len(keys) == 4, (err, keys)    # the runbook's list for the box: v3.0, c1 and v3crowd beside the FRONT_* line
E.FRONT_FAMILIES[0] = fams[0]; E.FRONT_FAMILIES[K3] = v3f; E.WAVE_ROUTERS.add(fams[0]["trigger"]["router"]); E.ANY_TO_SELECTORS.update(s for s, _ in t3["shapes"])
E.state["delayed"] = True; E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"; STAKE3 = int(0.0058e18)
def v3_dry_ret(p, pos):
    """send_sell's dry_ret, recomputed: our buy put into the price copy, the sell of the tokens it got, the two swaps' gas"""
    sp = v4math.sqrt_after_buy(p["sp"], p["liq"], E.net_of_fee(STAKE3, 100))
    return round((v4math.sell_out_int(int(sp), p["liq"], pos["feed_tokens"], 100) - STAKE3 - E.round_trip_gas_wei()) / STAKE3, 4)
# the crowd's exit: armed and fired (dry) in the launch block; a stranger's small buy ahead of ours; the crowd's first buy behind ours (+ 3 after it) starts the clock
reset(); E.state["nonce"] = 1000; E.state["front_halted"] = None; E.state["fam_halted"].clear(); L = 14000
E.ingest(frame(L, [signed(DEPLOYER, V3_NPM, 0, V3_IN, 20)])); p = E.state["armed"].get(V3_PID); pos = E.state["position"]; wf = events("would_fire")[-1]; a = events("armed")[-1]
assert p and p["dex"] == "v3" and p["fam"] == "v3crowd" and p["eligible"] and p["liq"] == V3["liq"] > 0 and p["tick0"] == V3["hi"] and p["token"] == V3["token"][2:] and p["status"] == "fired", a
assert a["dex"] == "v3" and a["eth_pair"] and a["fingerprint"] == "known" and a["tick_spacing"] == 1 and events("launch")[-1]["fam"] == "v3crowd"
assert pos and pos["dry"] and pos["dex"] == "v3" and (pos["fire_seq"], pos["plan_buy_seq"], pos["send_after"], pos["plan_sell_seq"]) == (L, L + 2, 76, L + 78) and pos["stake"] == STAKE3 \
    and len(SENT) == 0 and wf["fam"] == "v3crowd" and wf["buy_tx"] is None and wf["plan_buy_seq"] == L + 2, pos
E.ingest(frame(L + 1, [signed(OUTSIDER, UR, int(0.001e18), "0x12345678" + w(V3["token"]), 70)])); sp1 = p["sp"]   # 0.001 ETH with ETH as its value: under min_eth, ahead of ours
assert p["buys"] == 1 and p["first_buy"] is None and sp1 == v4math.sqrt_after_buy(float(V3["sqrt_p"]), V3["liq"], E.net_of_fee(int(0.001e18), 100))
E.ingest(frame(L + 2, [])); assert pos["buy_seq"] == L + 2 and pos["feed_tokens"] == v4math.buy_out_int(int(sp1), V3["liq"], STAKE3, 100)   # the virtual buy, behind the stranger's
E.ingest(frame(L + 5, [signed(CROWD, B1["to"], 0, B1["input"], 71)]))                                    # the crowd's 0.016 ETH (3593564c, 484 bytes) through its contract
fb = events("first_buy")[-1]; assert p["first_buy"] == L + 5 and fb["trigger"] is True and fb["value"] == B1["amount_wei"] == int(0.016e18) and fb["fam"] == "v3crowd" and fb["offset"] == 5, fb
assert p["sp"] == v4math.sqrt_after_buy(sp1, V3["liq"], E.net_of_fee(B1["amount_wei"], 100)) and pos["exit_seq"] == L + 5 + 18 and not pos["sell_sent"], (pos["exit_seq"], pos["sell_sent"])
o = 4 + 32 * 13; b1 = bytes.fromhex(B1["input"][2:]); tb = bytes.fromhex(V3["token"][2:]); assert b1[o:o + 43] == E.WETH_BYTES + (100).to_bytes(3, "big") + tb
sell1 = b1[:o] + tb + (100).to_bytes(3, "big") + E.WETH_BYTES + b1[o + 43:]; other = b1.replace(tb, b"\x77" * 20); sp_ = p["sp"]
E.ingest(frame(L + 6, [signed(CROWD, B1["to"], 0, "0x" + sell1.hex(), 72), signed(CROWD, B1["to"], 0, "0x" + other.hex(), 73), signed(CROWD, B1["to"], 0, B1["input"][:-2], 74)]))
assert p["sp"] == sp_ and p["buys"] == 2, "the crowd's sell (the path from the token), another token's buy or another length taken for a buy"
word_form = bytes.fromhex("3593564c") + bytes(32 * 12) + tb.rjust(32, b"\0") + bytes(484 - 4 - 32 * 13); assert E.trigger_word(t3, "ab" * 20, word_form, p) == 9   # the token as an address word
E.ingest(frame(L + 10, [signed(CROWD, B2["to"], 0, B2["input"], 75)]))                                  # the crowd's 0.11 ETH (a0193551, 452 bytes): the price moves, the clock stays
assert p["buys"] == 3 and p["eth_in"] == int(0.001e18) + B1["amount_wei"] + B2["amount_wei"] and pos["exit_seq"] == L + 23 and not pos["sell_sent"]
for s_ in range(L + 11, L + 23):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(L + 23, [])); ws = events("would_sell")[-1]
assert pos["sell_sent"] and pos["sell_seq_sent"] == L + 23 and ws["why"].startswith("the crowd's buy behind ours (0.0160 ETH in its call shape, our buy + 3)") and ws["after_buy"] == 21, ws
assert ws["dry_ret"] == v3_dry_ret(p, pos) and 0.03 < ws["dry_ret"] < 0.2 and len(SENT) == 0, ws                    # the crowd's 0.126 ETH behind our 0.0058
assert wait_for(lambda: any(e.get("dry") and e.get("fam") == "v3crowd" and e.get("dry_ret") == ws["dry_ret"] for e in events("trade_done")), 3.0), "no dry trade_done with dry_ret"
# no crowd: the cap (the sell when the feed shows launch + 78); the family set live behind the parser's back still never sends
reset(); E.state["nonce"] = 1010; v3f["dry_run"] = False; L = 14200
E.ingest(frame(L, [signed(DEPLOYER, V3_NPM, 0, V3_IN, 21)])); pos = E.state["position"]; p = E.state["armed"][V3_PID]
assert pos and pos["dry"] and len(SENT) == 0 and events("would_fire")[-1]["fam"] == "v3crowd", "a V3 family went live"
for s_ in range(L + 1, L + 78):
    E.ingest(frame(s_, [])); assert not pos["sell_sent"], s_
E.ingest(frame(L + 78, [])); ws = events("would_sell")[-1]
assert pos["sell_sent"] and pos["sell_seq_sent"] == L + 78 and ws["why"].startswith("deadline: launch + 78, the V3 line's cap") and ws["dry_ret"] == v3_dry_ret(p, pos) and -0.003 < ws["dry_ret"] < 0, ws
v3f["dry_run"] = True
# the crowd's buy ahead of ours (+ 1) starts no clock; one at + 70 would end its wave past the cap: the cap first
reset(); E.state["nonce"] = 1020; L = 14400
E.ingest(frame(L, [signed(DEPLOYER, V3_NPM, 0, V3_IN, 22)])); pos = E.state["position"]
E.ingest(frame(L + 1, [signed(CROWD, B1["to"], 0, B1["input"], 76)])); E.ingest(frame(L + 2, []))
assert pos["buy_seq"] == L + 2 and pos["exit_seq"] is None and events("first_buy")[-1]["offset"] == 1
E.ingest(frame(L + 70, [signed(CROWD, B2["to"], 0, B2["input"], 77)])); assert pos["exit_seq"] == L + 88
E.ingest(frame(L + 77, [])); assert not pos["sell_sent"]
E.ingest(frame(L + 78, [])); assert pos["sell_sent"] and events("would_sell")[-1]["why"].startswith("deadline: launch + 78") and events("would_sell")[-1]["dry_ret"] > 0.03
# a mirrored launch (WETH as token1, a real one) is logged, not armed; the launch's calldata to another contract (v4's PositionManager included) is no launch
reset(); E.ingest(frame(14600, [signed(DEPLOYER, V3_NPM, 0, V3["mirrored"]["launch_input"], 23)])); a = events("armed")[-1]
assert a["pid"] == V3["mirrored"]["pool"] and not a["eligible"] and "WETH is token1" in a["why"] and E.state["position"] is None and not E.state["armed"], a
n_launch = len(events("launch")); E.ingest(frame(14601, [signed(DEPLOYER, POSM, 0, V3_IN, 24), signed(DEPLOYER, "0x" + "99" * 20, 0, V3_IN, 25), signed(DEPLOYER, V3_NPM, 1, V3_IN, 26)]))
assert len(events("launch")) == n_launch and not E.state["armed"]
# in the same run: C-1 (value 0, v4's PositionManager) arms as before; the 2.4333 line trades live as before
reset(); E.ingest(frame(14700, [signed(DEPLOYER, POSM, 0, C1["launch_input"], 27)])); c = E.state["armed"].get(C1_PID); assert c and c["fam"] == "c1" and "dex" not in c and c["status"] == "armed"
reset(); E.state["nonce"] = 1030; p4 = front_launch(14800, 28); pos = E.state["position"]
assert p4 and p4["fam"] == "v2.433" and "dex" not in p4 and pos and not pos["dry"] and pos["send_after"] == E.FRONT_HOLD_BLOCKS and "exit_seq" not in pos and len(SENT) == 1, pos
E.ingest(frame(14801, [SENT[-1][1]])); E.ingest(frame(14809, [signed(CROWD, BOT, int(0.12e18), FBUY, 78)]))
assert pos["buy_seq"] == 14801 and pos["sell_sent"] and pos["sell_why"].startswith("take profit")
d = front_close(pos, 14801, 14810, int(E.FRONT_STAKE_WEI * 1.09)); assert d["fam"] == "v2.433" and d["ret"] > 0.08 and not d.get("pulled_before_sell") and E.state["front_halted"] is None, d
del E.FRONT_FAMILIES[0], E.FRONT_FAMILIES[K3]; E.WAVE_ROUTERS.discard(fams[0]["trigger"]["router"]); E.ANY_TO_SELECTORS.clear()
E.state["delayed"] = any(f["fire_at"] or f["trigger"] for f in E.FRONT_FAMILIES.values()); reset(); E.FRONT = False; E.ENTRY = "follow"
print("ok a V3 family (the crowd line): the 836-byte launch decodes as the chain has it (pool by CREATE2, price on the top tick, liquidity), arms by its PositionManager beside C-1 (both value 0) and fires dry in its launch block (+ 2); the crowd's buys move the price copy, its first behind ours sells 18 blocks later with dry_ret, the cap at launch + 78; its sells, other tokens, a mirrored launch and a live setting never trade; bad JSON is refused at start, never a crash; the 2.4333 line trades as before")

for _f in (E.LOG_PATH, E.LOG_PATH + ".1"):
    if os.path.exists(_f): os.remove(_f)
