"""Run the real flip_engine (ingest on the main thread, watchdog thread) against a clocked fake chain: block n is produced at
t0 + n*BT, the feed delivers it LAG seconds later; the fake sequencer puts a posted tx into the next block and (like Nitro's
PublishTransaction) replies once that block is made. Measures the sell's landing block minus the buy's, with no buy behind ours
(the deadline/fallback path). KIND4: our buy is alone in its block and the feed sends it as a bare kind-4 message."""
import os, sys, json, time, base64, tempfile, threading, math
LOG = tempfile.mktemp(suffix=".jsonl")
from eth_account import Account
from eth_utils import keccak, to_checksum_address
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY)
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": "0x" + "f1"*20, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY,
    "LAUNCHERS": "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "RECEIPT_TIMEOUT_S": "0.05", "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt"})
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
BT = 0.103
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
TOKEN = "0x" + "ab"*20; PID = "0x" + "77"*32; SQRT_P0 = 1292187213925453985058262482146976; TICK0 = 194000; LIQ = 61_310_000_000_000_000_000_000
RECEIPTS = {}
def launch_receipt():
    PM = E.POOL_MANAGER
    return {"status": "0x1", "blockNumber": "0x1", "logs": [
        {"address": PM, "topics": ["0x" + E.T_INIT, PID, "0x" + w(0), "0x" + w(TOKEN)], "data": "0x" + w(1134) + w(200) + w(0) + w(SQRT_P0) + w(TICK0)},
        {"address": PM, "topics": ["0x" + E.T_ML, PID, "0x" + w(ACCT.address)], "data": "0x" + w(-887200) + w(TICK0) + w(LIQ) + w(0)}]}
def fake_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionReceipt": return RECEIPTS.get(params[0].lower())
    if method == "eth_getBlockByNumber": return {"baseFeePerGas": hex(20_000_000), "number": "0x1"}
    if method == "eth_getTransactionCount": return "0x5"
    if method == "eth_getLogs": return []
    raise RuntimeError(method)
E.rpc = fake_rpc
def signed(key, to, value, data, nonce):
    return bytes(Account.from_key(key).sign_transaction({"to": to_checksum_address(to), "value": value, "data": data, "gas": 300000, "gasPrice": 10**8, "nonce": nonce, "chainId": 4663}).raw_transaction)
BUY_DATA = "0x24856bc3" + w(0x40) + w(0x80) + w(1) + w(TOKEN) + w(3000)
class Chain:
    def __init__(s, t0): s.t0 = t0; s.extra = {}; s.landed = {}
    def head_at(s, t): return math.floor((t - s.t0) / BT)
class FakeSeq:
    def __init__(s, ch, rtt): s.ch = ch; s.rtt = rtt; s.lock = threading.Lock()
    def post(s, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); now = time.monotonic()
        time.sleep(s.rtt / 2)                                        # one way to the sequencer
        blk = s.ch.head_at(time.monotonic()) + 1                     # into the next block it makes
        s.ch.extra.setdefault(blk, []).append(raw); s.ch.landed[i] = blk
        wait = s.ch.t0 + blk * BT - time.monotonic()
        if wait > 0: time.sleep(wait)                                # Nitro replies once the tx is sequenced
        time.sleep(s.rtt / 2)
        return {"result": "0x" + keccak(raw).hex()}
def frame(seq, raws, ts, kind4=False):
    if kind4 and len(raws) == 1: body = b"\x04" + raws[0]
    else: body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": ts}, "l2Msg": base64.b64encode(body).decode()}}}]})
started = [False]
def run(lag, kind4=False, rtt=0.02, trig_at=12, nblocks=26):
    E.state.update({"armed": {}, "position": None, "trades_today": 0, "pnl_today_usd": 0.0, "seq": 0, "nonce": 5, "halted": None, "base_fee": 20_000_000, "fee_at": time.monotonic()})
    E.STALE_S = 2.5; E.state["recent"].clear()
    wall0 = time.time(); t0 = time.monotonic() + 0.05; ch = Chain(t0); E.SENDER = FakeSeq(ch, rtt); E.SIGNER = ACCT
    if not started[0]: threading.Thread(target=E.watchdog, daemon=True).start(); started[0] = True
    launch = signed("0x" + "22"*32, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", 0, "0x2fcb9108" + w(1), int(time.time()*1000) % 10**9)
    RECEIPTS["0x" + keccak(launch).hex()] = launch_receipt()
    crowd = signed("0x" + "33"*32, "0x8876789976decbfcbbbe364623c63652db8c0904", int(0.04e18), BUY_DATA, int(time.time()*1000) % 10**9)
    base = {0: [launch], trig_at: [crowd]}
    for n in range(nblocks):
        due = t0 + n * BT + lag
        d = due - time.monotonic()
        if d > 0: time.sleep(d)
        if n == 1:
            t_ = time.time()
            while PID not in E.state["armed"] and time.time() - t_ < 2: time.sleep(0.005)
        raws = base.get(n, []) + ch.extra.get(n, [])
        E.ingest(frame(100000 + n, raws, int(wall0 + n * BT), kind4=kind4))
    time.sleep(0.6)
    pos_b = ch.landed.get(0); pos_s = ch.landed.get(1)
    evs = [json.loads(l) for l in open(LOG)]
    ss = [e for e in evs if e["ev"] == "sell_sent"]; why = ss[-1]["why"][:45] if ss else None
    E.state["position"] = None
    globals().setdefault("ALL", []).extend(evs); open(LOG, "w").close()
    return (pos_b - trig_at if pos_b is not None else None), (pos_s - pos_b if pos_s is not None and pos_b is not None else None), why
print("lag_s  kind4  buy=trig+  sell_landed=buy+  sent_by")
for kind4 in (False, True):
    for lag in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0):
        for rep in range(2):
            b, s, why = run(lag, kind4)
            print(f"{lag:5.2f}  {str(kind4):5s}  {b}  {s}  {why}")
