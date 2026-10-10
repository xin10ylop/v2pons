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
    E.state["front_pnl_today_usd"] = 0.0; E.state["arming"].clear()


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
assert d["pulled_before_sell"] is True and d["pull_after_buy_blocks"] == 5 and d["sell_after_buy_blocks"] == 5 and E.state["halted"] and os.path.exists(E.HALT_FILE), d
assert any(e["what"].startswith("live trading halted") for e in events("alarm"))
reset(); E.state["nonce"] = 95; p = do_launch(1600); E.ingest(frame(1631, [signed(CROWD, UR, TRIG, BUY_DATA, 35)]))
assert E.state["position"] is None and events("skip")[-1]["why"].startswith("halted"), events("skip")[-1]
E.state["halted"] = None; os.remove(E.HALT_FILE); LOGS.clear()
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
class HangingSender(FakeSender):
    def post(self, i, body, retry=True):
        r = super().post(i, body, retry)
        if len(SENT) == 1:
            gate.wait(10)                                                      # the buy's reply: held until the sell is out
        return r
E.SENDER = HangingSender(); SYNC_BUY[0] = False
t0 = time.time(); E.ingest(frame(3231, [signed(CROWD, UR, TRIG, BUY_DATA, 61)])); pos = E.state["position"]
assert pos is not None and time.time() - t0 < 0.5 and E.state["nonce"] == 242, "the feed waited on the buy's reply"
assert wait_for(lambda: len(SENT) == 1); buy_raw = SENT[0][1]
E.ingest(frame(3232, [])); E.ingest(frame(3233, [buy_raw])); E.ingest(frame(3234, [])); E.ingest(frame(3235, []))
assert pos["buy_seq"] == 3233 and pos["sell_sent"] and "buy_reply" not in pos and wait_for(lambda: len(SENT) == 2), "the sell waited on the buy's reply"
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
d = dict(E.decode_launch(FIN)); assert E.front_mismatch(d, d["mint_liq"]) is None and E.front_fingerprint(d) == []
for k, v, why in (("fee", 10000, "fee"), ("hooks", "11" * 20, "hook")):
    assert why in E.front_mismatch({**d, k: v}, d["mint_liq"]), (k, E.front_mismatch({**d, k: v}, d["mint_liq"]))
assert E.front_mismatch(d, 0) and E.front_fingerprint({**d, "fee": 3000, "tick_spacing": 60, "mint_liq": 1}) == ["fee 3000", "tick spacing 60", "liquidity 1"]
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
E.FRONT = False; E.ENTRY = "follow"
print("ok a sell sent for a position no longer in the slot does nothing; tx_buy's stake 0 is 0")
os.remove(LOG)
