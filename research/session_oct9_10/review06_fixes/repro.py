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
ROOT = "/home/user/v2pons"; LOG = tempfile.mktemp(suffix=".jsonl")
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


TRIG = int(0.04e18)
done_at = lambda n: [e for e in events("trade_done") if e.get("nonce") == n]

# ---- A1: lost buy that never went in; settle's exact refresh fails once -> nonce stuck high forever
reset(); E.state["nonce"] = 170; NONCE_ON_CHAIN[0] = hex(170); p = do_launch(2500)
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}]
E.ingest(frame(2531, [signed(CROWD, UR, TRIG, BUY_DATA, 53)])); pos = E.state["position"]; assert pos and E.state["nonce"] == 172
REPLIES[:] = [{"error": {"code": -32000, "message": "nonce too high"}}] * E.SELL_TRIES
E.RECEIPT_TIMEOUT_S = 0.3
rpc_ok = E.rpc
def flaky(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionCount": raise RuntimeError("eth_getTransactionCount: HTTP Error 429")
    return rpc_ok(method, params, tries, timeout)
E.rpc = flaky
for s_ in range(2532, 2538): E.ingest(frame(s_, []))
assert wait_for(lambda: done_at(170), 4.0); time.sleep(0.3)
E.rpc = rpc_ok
print("A1 after settle: engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16), "position", E.state["position"], "trades_today", E.state["trades_today"])
# next launch: the buy at 172 is refused 'nonce too high'; the rejected path's refresh (exact=False) keeps 172
E.state["armed"].clear(); SENT.clear()
p = do_launch(2600)
REPLIES[:] = [{"error": {"code": -32000, "message": "nonce too high: address x, tx: 172 state: 170"}}]
E.ingest(frame(2631, [signed(CROWD, UR, TRIG, BUY_DATA, 54)])); time.sleep(0.3)
print("A1 next trade: rejected", bool(events("buy_rejected")), "engine nonce after the rejected path's refresh", E.state["nonce"], "(chain 170) -> stuck")

# ---- A2: buy lands but reverts; sell never accepted (4 transient refusals) -> rs None, no halt, exact=False keeps nonce+2
reset(); E.state["nonce"] = 300; p = do_launch(3000); NONCE_ON_CHAIN[0] = hex(301)
E.ingest(frame(3031, [signed(CROWD, UR, TRIG, BUY_DATA, 60)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(3032, [])); E.ingest(frame(3033, [buy_raw]))
REPLIES[:] = [{"error": {"code": -32000, "message": "sequencer temporarily not available"}}] * E.SELL_TRIES
t0 = time.time(); E.ingest(frame(3034, [])); E.ingest(frame(3035, []))
RECEIPTS["0x" + pos["buy_hash"]] = {"status": "0x0", "blockNumber": hex(3033), "gasUsed": hex(40000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
assert wait_for(lambda: done_at(300), 4.0); time.sleep(0.2)
ss = [e for e in events("sell_sent") if e["nonce"] == 301][-1]
print("A2: sell tries", ss["tries"], "halted", E.state["halted"], "engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16))

# ---- B: buy filled; 4 fast transient refusals of the sell -> given up within ms, never sent again
reset(); E.state["nonce"] = 400; p = do_launch(4000); NONCE_ON_CHAIN[0] = hex(401)
E.ingest(frame(4031, [signed(CROWD, UR, TRIG, BUY_DATA, 61)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(4032, [])); E.ingest(frame(4033, [buy_raw]))
REPLIES[:] = [{"error": {"code": -32000, "message": "sequencer temporarily not available"}}] * E.SELL_TRIES
t0 = time.time(); E.ingest(frame(4034, [])); E.ingest(frame(4035, []))
assert wait_for(lambda: any(e["ev"] == "sell_sent" and e["nonce"] == 401 for e in events()), 3.0); t_give = time.time() - t0
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(4033, -E.STAKE_WEI, pos["feed_tokens"])
for s_ in range(4036, 4050): E.ingest(frame(s_, []))
assert wait_for(lambda: done_at(400), 4.0)
print(f"B: gave up after {t_give*1000:.0f} ms (+RTTs live); sell sends total", sum(1 for i, r in SENT if r == pos["sell_raw"]), "halted:", E.state["halted"])
E.state["halted"] = None
try: os.remove(E.HALT_FILE)
except Exception: pass

# ---- C: launcher code fetched before the RPC has the deploy block -> '0x' -> never eligible
E.ENTRY = "seat"; E.LAUNCH_SELECTORS = {"2fcb9108"}; FRESH = "0x" + "5e" * 20
OP_CODE = "0x" + "60806040" * 50; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}
reset(); E.state["nonce"] = 500
lag = {"until": time.time() + 0.15}
def lagging(method, params, tries=4, timeout=10):
    if time.time() < lag["until"]:
        if method == "eth_getCode": return "0x"                 # the backend has not seen the deploy block yet
        if method == "eth_getTransactionReceipt": return None   # nor the launch block
    if method == "eth_getCode": return OP_CODE
    return rpc_ok(method, params, tries, timeout)
E.rpc = lagging
raw = signed(DEPLOYER, FRESH, 0, "0x2fcb9108" + w(1), 9); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt(h)
E.ingest(frame(5000, [raw])); assert wait_for(lambda: PID in E.state["armed"], 3)
p = E.state["armed"][PID]; print("C: armed after", p["arm_ms"], "ms; eligible", p["eligible"], "launcher_code", p["launcher_code"])
E.rpc = rpc_ok
os.remove(LOG)
