import os, sys, json, time, base64, tempfile
from eth_account import Account
from eth_utils import keccak, to_checksum_address
ROOT = "/home/user/v2pons"; LOG = tempfile.mktemp(suffix=".jsonl")
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY); RELAY = "0x" + "f1" * 20
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY, "FRONT": "1", "FRONT_DRY_RUN": sys.argv[1],
                   "SELL_FALLBACK_S": "100", "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt"})
sys.path.insert(0, os.path.join(ROOT, "src"))
import flip_engine as E
SENT = []
class FS:
    def post(self, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); SENT.append(raw); return {"result": "0x" + keccak(raw).hex()}
E.rpc = lambda m, p, tries=4, timeout=10: None if m == "eth_getTransactionReceipt" else ("0x5" if m == "eth_getTransactionCount" else [])
E.SENDER = FS(); E.SIGNER = ACCT; E.state["nonce"] = 5; E.state["base_fee"] = 20_000_000
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
def signed(key, to, value, data, nonce):
    return bytes(Account.from_key(key).sign_transaction({"to": to_checksum_address(to), "value": value, "data": data, "gas": 300000, "gasPrice": 10 ** 8, "nonce": nonce, "chainId": 4663}).raw_transaction)
def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})
FX = json.load(open(os.path.join(ROOT, "tests", "data", "front_launch.json")))
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
FBUY = "0xc1120e3d" + w(FX["token"]) + w(0) * 8
E.ingest(frame(5000, [signed("0x" + "22" * 32, POSM, E.FRONT_VALUE_WEI, FX["input"], 1)]))
pos = E.state["position"]; print("fired:", pos["entry"], "dry" if pos["dry"] else "live")
if not pos["dry"]:
    E.ingest(frame(5001, [SENT[0]]))
else:
    E.ingest(frame(5001, [])); E.ingest(frame(5002, []))
print("our buy at", pos["buy_seq"])
other = int(0.011e18)
E.ingest(frame(5004, [signed("0x" + "33" * 32, "0x" + "65" * 20, other, FBUY, 1)]))   # an outsider's 0.011 ETH buy behind ours
print("after outsider 0.011: sell_sent", pos["sell_sent"])
for s in range(5005, 5009): E.ingest(frame(s, []))
E.ingest(frame(5009, [signed("0x" + "44" * 32, BOT, int(0.12e18), FBUY, 1)]))       # the bot's 0.12 buy (would revert with >= ~0.012 ahead)
print("after bot buy: sell_sent", pos["sell_sent"], "why", pos.get("sell_why"), "tp_ret", pos["tp_ret"])
time.sleep(1.3)
for l in open(LOG):
    e = json.loads(l)
    if e["ev"] in ("would_sell", "sell_sent", "trade_done"): print({k: e.get(k) for k in ("ev", "why", "tp_ret", "after_buy")})
