"""The flip engine against a scripted feed: real signed transactions in real L2 batch frames, the RPC and the sequencer stubbed.
Relay route: a launch is armed from its receipt, the operator's first real-size buy fires the buy at the reserved nonce with the
predicted minOut, our own buy seen in the feed fixes the sell's block, the sell goes out at buy block + HOLD - LEAD, both
receipts make the trade_done line. Then the gates (dust, fee tier, late first buy, position open, daily cap), the dry run, stale
frames. Router route: the buy is the crowd's transaction from the wallet (type 2, to the router, the stake as the value, the
crowd's bytes), the fleet's two approvals follow it at the next nonces, the sell is signed with the amount the buy's receipt shows
and sent at the fourth nonce; the sell's block before the receipt (the feed's token count goes, less the margin); a reverted buy (no
sell). Release 0.3, the exit: a buy behind ours that pays TAKE_PROFIT sells at once; one that does not leaves the deadline; the
pool's price follows every buy on the feed (a dust buy before the trigger moves minOut), buys that landed before the launch was
armed are replayed onto it; a pull at or before our sell halts live trading (the halt file) until it is removed; BUY_DELAY_BLOCKS;
the dry run's take-profit.
Plain script: python3 tests/test_engine.py"""
import os, sys, json, time, base64, tempfile, threading
import rlp
from eth_account import Account
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); LOG = tempfile.mktemp(suffix=".jsonl")
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY); RELAY = "0x" + "f1" * 20; LAUNCHER = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY, "LAUNCHERS": LAUNCHER, "STAKE_ETH": "0.0012", "ROUTE": "relay",
                   "HOLD_BLOCKS": "4", "SELL_LEAD_BLOCKS": "2", "SELL_FALLBACK_S": "100", "FEE_MAX_PPM": "9999", "TRIGGER_MAX_BLOCKS": "150", "MAX_TRADES_PER_DAY": "2", "DAILY_STOP_USD": "15",
                   "TAKE_PROFIT": "0.01", "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt"})
sys.path.insert(0, os.path.join(ROOT, "src"))
import flip_engine as E
import v4math, ur

PM = E.POOL_MANAGER; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
TOKEN = "0x" + "ab" * 20; PID = "0x" + "77" * 32; SQRT_P0 = 1292187213925453985058262482146976; TICK0 = 194000; LIQ = 61_310_000_000_000_000_000_000
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
RECEIPTS = {}; LOGS = []; SENT = []


# --- stubs
def fake_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionReceipt": return RECEIPTS.get(params[0].lower())
    if method == "eth_getLogs": return LOGS
    if method == "eth_getTransactionCount": return "0x5"
    if method == "eth_getBlockByNumber": return {"baseFeePerGas": hex(20_000_000), "number": "0x1"}
    raise RuntimeError(method)
E.rpc = fake_rpc


class FakeSender:
    def post(self, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); SENT.append((i, raw)); return {"result": "0x" + keccak(raw).hex()}
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


# --- the router route
PERMIT2 = ur.PERMIT2; KEYD = {"c0": "0" * 40, "token": TOKEN[2:], "fee": 1134, "tick_spacing": 200, "hooks": "0" * 40}
typed = lambda raw: (raw[0], rlp.decode(raw[1:]))               # type 2: [chainId, nonce, maxPrio, maxFee, gas, to, value, data, accessList, v, r, s]


def router_buy_receipt(block, tokens):
    return {"status": "0x1", "blockNumber": hex(block), "gasUsed": hex(118000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2",
            "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, PID, "0x" + w(ur.UR)], "data": "0x" + w(-E.STAKE_WEI) + w(tokens) + w(SQRT_P0) + w(LIQ) + w(0) + w(0)},
                     {"address": TOKEN, "topics": ["0x" + ur.T_TRANSFER, "0x" + w(PM), "0x" + w(ACCT.address)], "data": "0x" + w(tokens)}]}


def router_sell_receipt(block, eth_out, tokens_in):
    return {"status": "0x1", "blockNumber": hex(block), "gasUsed": hex(128000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x1",
            "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, PID, "0x" + w(ur.UR)], "data": "0x" + w(eth_out) + w(-tokens_in) + w(SQRT_P0) + w(LIQ) + w(0) + w(0)}]}


def approval_receipts(pos):
    for h in pos["approve_hashes"]:
        RECEIPTS["0x" + h] = {"status": "0x1", "blockNumber": hex(834), "gasUsed": hex(46000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x4", "logs": []}


def fire_router(seq_launch, seq_trig, nonce0, crowd_nonce):
    """a launch, the crowd's first buy, the router buy and its two approvals sent; returns (pos, buy_raw, expected tokens, the trigger's ts)"""
    E.state["nonce"] = nonce0; p = do_launch(seq_launch); ts = int(time.time())
    E.ingest(frame(seq_trig, [signed(CROWD, UR, int(0.04e18), BUY_DATA, crowd_nonce)], ts=ts))
    pos = E.state["position"]; assert pos is not None and pos["route"] == "router" and pos["nonce"] == nonce0 and pos["sell_nonce"] == nonce0 + 3, pos
    assert wait_for(lambda: len(SENT) == 3), "the buy and its two approvals were not all sent"
    x_trig = int(0.04e18) - (int(0.04e18) * 1134 + 999_999) // 1_000_000; sp1 = int(v4math.sqrt_after_buy(SQRT_P0, LIQ, x_trig)); expected = v4math.buy_out_int(sp1, LIQ, E.STAKE_WEI, 1134)
    return pos, SENT[0][1], expected, ts


# --- 5. the router route: the crowd's buy from the wallet, the fleet's approvals behind it, the sell with the receipt's exact amount
reset(); E.DRY_RUN = False; E.ROUTE = "router"
pos, buy_raw, expected, ts = fire_router(800, 830, 20, 16)
t, f = typed(buy_raw); assert t == 2 and SENT[0][0] == 0
assert int.from_bytes(f[1], "big") == 20 and f[5].hex() == ur.UR[2:] and int.from_bytes(f[6], "big") == E.STAKE_WEI and int.from_bytes(f[4], "big") == 220000, "the buy is not the crowd's transaction"
assert int.from_bytes(f[2], "big") == 20_000_000 and int.from_bytes(f[3], "big") == 60_000_000, "the crowd's tip and the fee cap"
assert f[7].hex() == ur.buy_calldata(KEYD, E.STAKE_WEI, int(expected * (1 - E.BUY_SLIP)), ts + 3)[2:], "the buy's calldata is not the crowd's"
ta, fa = typed(SENT[1][1]); tp, fp = typed(SENT[2][1]); assert SENT[1][0] == 1 and SENT[2][0] == 1
assert ta == 2 and int.from_bytes(fa[1], "big") == 21 and fa[5].hex() == TOKEN[2:] and fa[7].hex() == ur.approve_permit2_calldata()[2:] and int.from_bytes(fa[4], "big") == 120000, "the token approval"
assert tp == 2 and int.from_bytes(fp[1], "big") == 22 and fp[5].hex() == PERMIT2[2:] and fp[7].hex() == ur.permit2_approve_calldata(TOKEN[2:])[2:] and int.from_bytes(fp[4], "big") == 140000, "the Permit2 approval"
assert E.state["nonce"] == 24 and events("fire")[-1]["approve_hashes"] == pos["approve_hashes"] and events("approvals_sent")
tokens = expected - 12345                                                           # the fill, a little under the prediction
RECEIPTS["0x" + pos["buy_hash"]] = router_buy_receipt(833, tokens); approval_receipts(pos)
assert wait_for(lambda: pos["sell_raw"] is not None), "the sell was not signed from the receipt"
assert pos["sell_amount"] == tokens and pos["sell_amount_src"] == "receipt" and events("sell_ready")[-1]["tokens"] == tokens
E.ingest(frame(832, [])); E.ingest(frame(833, [buy_raw])); assert pos["buy_seq"] == 833
E.ingest(frame(834, [])); assert not pos["sell_sent"]
RECEIPTS["0x" + pos["sell_hash"]] = router_sell_receipt(837, int(E.STAKE_WEI * 1.05), tokens)
E.ingest(frame(835, []))                                                             # 833 + 4 - 2
assert pos["sell_sent"] and len(SENT) == 4 and SENT[3][0] == 0
tsl, fs = typed(SENT[3][1]); assert tsl == 2 and int.from_bytes(fs[1], "big") == 23 and fs[5].hex() == ur.UR[2:] and int.from_bytes(fs[6], "big") == 0
assert fs[7].hex() == ur.sell_calldata(KEYD, tokens, 0, 0)[2:], "the sell's calldata is not the fleet's"
done_at = lambda n: [e for e in events("trade_done") if e.get("nonce") == n]          # the dry run's trade_done lands a second late; pick by nonce
assert wait_for(lambda: done_at(20)), "no trade_done"
d = done_at(20)[-1]
assert d["route"] == "router" and d["buy"]["block"] == 833 and d["sell"]["block"] == 837 and d["hold_blocks"] == 4 and d["buy_offset"] == 3 and abs(d["ret"] - 0.05) < 1e-9, d
assert d["approvals"] == ["ok", "ok"] and d["sell_amount"] == tokens and d["tokens_left"] == 0 and d["gas_wei"] == (118000 + 128000 + 2 * 46000) * 20_000_000, d
assert E.state["position"] is None and E.state["trades_today"] == 1
print("ok router route: the crowd's buy from the wallet (type 2, to the router, the stake as the value, their bytes), the fleet's two approvals at the next nonces, the sell at the fourth nonce with the receipt's amount, trade_done priced")

# --- 6. the sell due before the buy's receipt: the feed's token count goes, less the margin; the leftover is reported
reset(); pos, buy_raw, expected, ts = fire_router(900, 930, 30, 17)
E.ingest(frame(932, [])); E.ingest(frame(933, [buy_raw])); E.ingest(frame(934, []))
E.ingest(frame(935, []))
amt = int(expected * (1 - E.SELL_AMOUNT_MARGIN))
assert pos["feed_tokens"] == expected and pos["sell_sent"] and len(SENT) == 4 and pos["sell_amount"] == amt and pos["sell_amount_src"].startswith("feed"), pos["sell_amount_src"]
tsl, fs = typed(SENT[3][1]); assert int.from_bytes(fs[1], "big") == 33 and fs[7].hex() == ur.sell_calldata(KEYD, amt, 0, 0)[2:]
tokens = expected                                                                    # the fill the feed predicted
RECEIPTS["0x" + pos["buy_hash"]] = router_buy_receipt(933, tokens); RECEIPTS["0x" + pos["sell_hash"]] = router_sell_receipt(937, int(E.STAKE_WEI * 0.95), amt); approval_receipts(pos)
assert wait_for(lambda: done_at(30))
d = done_at(30)[-1]; assert d["tokens_left"] == tokens - amt and d["sell_amount"] == amt and events("tokens_left") and E.state["halted"] is None, d
print("ok router route, the sell due before the receipt: the feed's count less the margin sold, the leftover (the margin) in the log")

# --- 7. a reverted buy on the router route: no sell, the position closes
reset(); pos, buy_raw, expected, ts = fire_router(1000, 1030, 40, 18)
RECEIPTS["0x" + pos["buy_hash"]] = {"status": "0x0", "blockNumber": hex(1033), "gasUsed": hex(40000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
assert wait_for(lambda: pos["buy_reverted"]) and events("buy_reverted")
approval_receipts(pos); E.ingest(frame(1033, [buy_raw]))
for s in range(1034, 1039):
    E.ingest(frame(s, []))
assert pos["sell_sent"] and len(SENT) == 3 and pos["sell_hash"] is None and events("sell_skipped")
assert wait_for(lambda: done_at(40))
d = done_at(40)[-1]; assert d["buy"]["status"] == "reverted" and d["sell"] == "skipped: the buy reverted" and d["eth_in"] == 0 and E.state["position"] is None, d
print("ok router route, a reverted buy: no sell sent, the trade closed")

# --- 8. the router dry run builds the crowd's transaction and the approvals, sends nothing
reset(); E.DRY_RUN = True; E.state["nonce"] = 50; p = do_launch(1100); E.ingest(frame(1140, [signed(CROWD, UR, int(0.04e18), BUY_DATA, 19)]))
wf = events("would_fire")[-1]; assert wf["route"] == "router" and wf["buy_tx"]["to"] == E.UR_TO and wf["buy_tx"]["value"] == E.STAKE_WEI and wf["approve_tx"]["nonce"] == 51 and wf["permit2_tx"]["nonce"] == 52 and wf["sell_tx"]["nonce"] == 53 and len(SENT) == 0
for s in range(1141, 1145):
    E.ingest(frame(s, []))
assert events("would_sell")[-1]["seq"] == 1144 and len(SENT) == 0 and wait_for(lambda: E.state["position"] is None, 3.0)
print("ok router dry run: would_fire with the crowd's buy, the two approvals and the sell plan; nothing sent")


# --- release 0.3: the exit, the feed's pool price, the halt
net = lambda x: x - (x * 1134 + 999_999) // 1_000_000
TRIG = int(0.04e18)


def relay_trade(seq_launch, nonce0, crowd_nonce):
    """relay route: a launch, the crowd's first buy 31 blocks in, our buy landing two blocks later; returns (pos, buy_raw, buy block)"""
    E.state["nonce"] = nonce0; p = do_launch(seq_launch); t = seq_launch + 31
    E.ingest(frame(t, [signed(CROWD, UR, TRIG, BUY_DATA, crowd_nonce)])); pos = E.state["position"]; assert pos is not None and pos["route"] == "relay"
    buy_raw = SENT[0][1]; E.ingest(frame(t + 1, [])); E.ingest(frame(t + 2, [buy_raw])); assert pos["buy_seq"] == t + 2
    return pos, buy_raw, t + 2


# --- 9. take profit: a buy behind ours that does not pay TAKE_PROFIT leaves the position; the one that does sells at once
reset(); E.DRY_RUN = False; E.ROUTE = "relay"
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
reset(); E.ROUTE = "relay"
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
os.remove(LOG)
