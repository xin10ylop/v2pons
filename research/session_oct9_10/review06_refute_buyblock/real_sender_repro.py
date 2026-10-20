"""Engine c2d9fcb with its REAL Sender (http.client, 4 s socket timeouts, _retry) against a local HTTP 'sequencer'.
The sequencer answers eth_chainId (keepalive) normally and scripts the reply to our buy:
  silent1 : the buy's first connection gets no reply (the tx 'landed'); a new connection answers 'nonce too low'
  silent2 : the buy gets no reply on any connection
  reset   : the buy's first connection is closed right after the request is read; a new connection answers 'nonce too low'
  normal  : answered at once
Measures when the sell reaches the sequencer, from the buy's arrival, with the watchdog's 0.5 s time fallback running and the
feed delivering a block every 100 ms on its own thread."""
import os, sys, json, time, base64, tempfile, threading, socket, http.client
from eth_account import Account
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__)); LOG = tempfile.mktemp(suffix=".jsonl")
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY); RELAY = "0x" + "f1" * 20; LAUNCHER = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY, "LAUNCHERS": LAUNCHER, "STAKE_ETH": "0.0012",
                   "HOLD_BLOCKS": "4", "SELL_LEAD_BLOCKS": "2", "SELL_FALLBACK_S": "0.5", "FEE_MAX_PPM": "9999", "TRIGGER_MAX_BLOCKS": "150", "MAX_TRADES_PER_DAY": "50",
                   "TAKE_PROFIT": "9", "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt", "RECEIPT_TIMEOUT_S": "0.2"})
sys.path.insert(0, os.path.join(HERE, "eng"))
import flip_engine as E
assert E.RELEASE == "0.6"

PM = E.POOL_MANAGER; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
TOKEN = "0x" + "ab" * 20; PID = "0x" + "77" * 32; SQRT_P0 = 1292187213925453985058262482146976; TICK0 = 194000; LIQ = 61_310_000_000_000_000_000_000
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
RECEIPTS = {}

def fake_rpc(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionReceipt": return RECEIPTS.get(params[0].lower())
    if method == "eth_getLogs": return []
    if method == "eth_getTransactionCount": return "0x5"
    if method == "eth_getCode": return "0x"
    if method == "eth_getBlockByNumber": return {"baseFeePerGas": hex(20_000_000), "number": "0x1"}
    raise RuntimeError(method)
E.rpc = fake_rpc


# ---------------- the local 'sequencer'
MODE = ["normal"]; ARRIVALS = []          # (time, kind, conn_no)
conn_counter = [0]

def serve_conn(c, no):
    f = c.makefile("rb")
    try:
        while True:
            line = f.readline()
            if not line:
                return
            hdrs = {}
            while True:
                h = f.readline()
                if h in (b"\r\n", b"\n", b""):
                    break
                k, v = h.decode().split(":", 1); hdrs[k.strip().lower()] = v.strip()
            body = f.read(int(hdrs.get("content-length", "0"))); req = json.loads(body)
            method = req["method"]
            if method == "eth_sendRawTransaction":
                raw = bytes.fromhex(req["params"][0][2:]); kind = "buy" if raw == STATE["buy_raw"] else ("sell" if raw == STATE["sell_raw"] else "other")
                ARRIVALS.append((time.monotonic(), kind, no))
                first_buy = kind == "buy" and sum(1 for a in ARRIVALS if a[1] == "buy") == 1
                if kind == "buy" and MODE[0] == "silent2":
                    time.sleep(30); return
                if kind == "buy" and MODE[0] == "silent1" and first_buy:
                    time.sleep(30); return
                if kind == "buy" and MODE[0] == "reset" and first_buy:
                    c.shutdown(socket.SHUT_RDWR); c.close(); return
                if kind == "buy" and not first_buy:
                    out = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "nonce too low"}}
                else:
                    out = {"jsonrpc": "2.0", "id": 1, "result": "0x" + keccak(raw).hex()}
            else:
                out = {"jsonrpc": "2.0", "id": 1, "result": "0x1237"}
            data = json.dumps(out).encode()
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data)
    except Exception:
        return

def server(sock):
    while True:
        c, _ = sock.accept(); conn_counter[0] += 1
        threading.Thread(target=serve_conn, args=(c, conn_counter[0]), daemon=True).start()

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("127.0.0.1", 0)); srv.listen(64)
PORT = srv.getsockname()[1]; threading.Thread(target=server, args=(srv,), daemon=True).start()

class PlainConn(http.client.HTTPConnection):                     # the real Sender, HTTPS swapped for HTTP on localhost
    def __init__(self, host, port=None, timeout=None, context=None):
        super().__init__(host, port, timeout=timeout)
E.http.client.HTTPSConnection = PlainConn
STATE = {"buy_raw": None, "sell_raw": None}
E.SENDER = E.Sender(f"http://127.0.0.1:{PORT}/"); E.SIGNER = ACCT; E.state["base_fee"] = 20_000_000
time.sleep(1.5)                                                   # let the keepalive warm both slots


# ---------------- the scripted feed
def signed(key, to, value, data, nonce):
    from eth_utils import to_checksum_address
    return bytes(Account.from_key(key).sign_transaction({"to": to_checksum_address(to), "value": value, "data": data, "gas": 300000, "gasPrice": 10 ** 8, "nonce": nonce, "chainId": 4663}).raw_transaction)

def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})

def launch_receipt(fee=1134):
    return {"status": "0x1", "blockNumber": "0x64", "logs": [
        {"address": PM, "topics": ["0x" + E.T_INIT, PID, "0x" + w(0), "0x" + w(TOKEN)], "data": "0x" + w(fee) + w(200) + w("0" * 40) + w(SQRT_P0) + w(TICK0)},
        {"address": PM, "topics": ["0x" + E.T_ML, PID, "0x" + w(ACCT.address)], "data": "0x" + w(-887200) + w(TICK0) + w(LIQ) + w(0)}]}

DEPLOYER = "0x" + "22" * 32; CROWD = "0x" + "33" * 32
BUY_DATA = "0x24856bc3" + w(0x40) + w(0x80) + w(1) + w(TOKEN) + w(3000)
TRIG = int(0.04e18)

def wait_for(cond, s=3.0):
    t0 = time.time()
    while time.time() - t0 < s:
        if cond(): return True
        time.sleep(0.01)
    return False

# patch sign() to learn the buy/sell raws as the engine signs them
_sign = E.sign
def sign_spy(tx):
    raw, h = _sign(tx)
    if tx["data"].startswith("0x" + E.SEL_BUY): STATE["buy_raw"] = raw
    else: STATE["sell_raw"] = raw
    return raw, h
E.sign = sign_spy

threading.Thread(target=E.watchdog, daemon=True).start()          # the real watchdog (0.5 s time fallback)

def run(mode, base):
    MODE[0] = mode; ARRIVALS.clear(); STATE["buy_raw"] = STATE["sell_raw"] = None
    E.state["armed"].clear(); E.state["position"] = None; E.state["seq"] = 0; E.state["nonce"] = 100 + base // 100
    raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), base); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt()
    E.ingest(frame(base, [raw])); assert wait_for(lambda: PID in E.state["armed"])
    # the feed thread: the trigger, then one block every 100 ms (our buy lands in the first block after the send)
    t_feed = time.monotonic(); feed_done = [None]
    def feed():
        E.ingest(frame(base + 31, [signed(CROWD, UR, TRIG, BUY_DATA, base)]))      # fires the buy, synchronously, under the lock
        feed_done[0] = time.monotonic()
    fth = threading.Thread(target=feed); fth.start()
    def blocks():                                                                   # the chain moves on while the feed thread is stuck
        k = 32
        while k < 32 + 120:
            time.sleep(0.1)
            fr = frame(base + k, [STATE["buy_raw"]] if k == 32 and STATE["buy_raw"] else [])
            BLOCK_TIMES.append((base + k, time.monotonic()))
            k += 1
            PENDING.append(fr)
    BLOCK_TIMES = []; PENDING = []
    bth = threading.Thread(target=blocks, daemon=True); bth.start()
    fth.join()
    # the feed thread is free again: it now drains the frames that queued up meanwhile (as the websocket would)
    t_end = time.monotonic() + 12
    while time.monotonic() < t_end and not any(a[1] == "sell" for a in ARRIVALS):
        while PENDING:
            E.ingest(PENDING.pop(0))
        time.sleep(0.01)
    buy_t = min(a[0] for a in ARRIVALS if a[1] == "buy")
    sells = [a for a in ARRIVALS if a[1] == "sell"]
    pos = E.state["position"]
    reply = None
    for l in open(LOG):
        e = json.loads(l)
        if e["ev"] == "fire" and e["nonce"] == 100 + base // 100: reply = e.get("buy_reply"); send_ms = e.get("send_ms")
    sell_why = None
    for l in open(LOG):
        e = json.loads(l)
        if e["ev"] == "sell_sent" and e["nonce"] == 100 + base // 100 + 1: sell_why = e["why"]
    print(f"{mode:7s}: buy post returned after {1000 * (feed_done[0] - buy_t):6.0f} ms (send_ms {send_ms}), reply kind {E.reply_kind(reply)!r:10s}"
          f" sell reached the sequencer at +{1000 * (sells[0][0] - buy_t):6.0f} ms after the buy" if sells else f"{mode}: no sell", f"[{sell_why}]")
    wait_for(lambda: E.state["position"] is None, 5)
    E.state["position"] = None

for i, mode in enumerate(["normal", "reset", "silent1", "silent2"]):
    run(mode, 1000 * (i + 1))
os.remove(LOG)
