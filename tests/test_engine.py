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


def swap_receipt(block, a0, a1, index=3):
    return {"status": "0x1", "blockNumber": hex(block), "gasUsed": hex(120000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": hex(index),
            "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, PID, "0x" + w(RELAY)], "data": "0x" + w(a0) + w(a1) + w(SQRT_P0) + w(LIQ) + w(0) + w(0)}]}


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

# 15c. the node refuses our buy: no position, the nonce untouched
reset(); E.state["nonce"] = 160; p = do_launch(2400)
REPLIES[:] = [{"error": {"code": -32000, "message": "insufficient funds for gas * price + value"}}]
E.ingest(frame(2431, [signed(CROWD, UR, TRIG, BUY_DATA, 52)]))
assert E.state["position"] is None and events("buy_rejected") and E.state["trades_today"] == 0
print("ok a refused buy: no position")

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
assert wait_for(lambda: E.state["nonce"] == 170), E.state["nonce"]
E.RECEIPT_TIMEOUT_S = 25; NONCE_ON_CHAIN[0] = "0x5"
print("ok a lost buy that never went in: the sell retried and refused, the trade closed, the nonce back to the chain's")

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

# --- 16. ENTRY=auto: the original launcher gets the follow entry (its crowd 40-60 blocks in), a per-launch copy the seat
E.ENTRY = "auto"; E.LAUNCH_SELECTORS = {"2fcb9108"}; E.SEAT_CODE_HASHES = set(E.LAUNCHER_CODE_HASHES)
reset(); E.state["nonce"] = 220; p = do_launch(3000)                                    # through the original launcher (LAUNCHERS)
assert p["entry"] == "follow" and p["eligible"]
for s_ in range(3001, 3010):
    E.ingest(frame(s_, [])); assert E.state["position"] is None, "the follow entry fired before the crowd"
E.ingest(frame(3046, [signed(CROWD, UR, TRIG, BUY_DATA, 60)])); pos = E.state["position"]; assert pos and pos["trig_seq"] == 3046, "no follow fire on the crowd's first buy"
E.state["position"] = None
reset(); E.state["nonce"] = 230; p = seat_launch(3100, 6)                             # through a per-launch copy
assert p["entry"] == "seat" and p["eligible"]
for s_ in range(3101, 3106):
    E.ingest(frame(s_, []))
E.ingest(frame(3106, [])); pos = E.state["position"]; assert pos and pos["trig_seq"] == 3106 and pos["trig_value"] == 0, "no seat fire at launch + 6"
E.state["position"] = None; E.ENTRY = "follow"; E.LAUNCH_SELECTORS = set()
print("ok auto: the original launcher follows the crowd's first buy, a per-launch copy takes the seat at launch + 6")
os.remove(LOG)
