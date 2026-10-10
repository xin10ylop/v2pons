import os, sys, json, time, base64, tempfile
import rlp
from eth_account import Account
from eth_utils import keccak, to_checksum_address
ROOT = "/home/user/v2pons"; LOG = tempfile.mktemp(suffix=".jsonl")
KEY = "0x" + "11" * 32; ACCT = Account.from_key(KEY); RELAY = "0x" + "f1" * 20
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": ACCT.address.lower(), "PRIVATE_KEY": KEY, "FRONT": "1", "FRONT_DRY_RUN": "0",
                   "PULL_WATCH_S": "0", "HALT_FILE": LOG + ".halt", "SELL_FALLBACK_S": "100"})
sys.path.insert(0, os.path.join(ROOT, "src"))
import flip_engine as E, v4math
w = lambda x: ("%064x" % (x % (1 << 256)))
SENT = []
class FS:
    def post(self, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); SENT.append(raw); return {"result": "0x" + keccak(raw).hex()}
E.SENDER = FS(); E.SIGNER = ACCT; E.state["nonce"] = 5
E.rpc = lambda m, p, tries=4, timeout=10: None
def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})
FX = json.load(open(os.path.join(ROOT, "tests", "data", "front_launch.json")))
inp = FX["input"][2:]
fee_w = w(2500); sp_w = w(FX["sqrt_p"])
print("fee word occurrences:", inp.count(fee_w), "sqrtP word occurrences:", inp.count(sp_w))
fake = inp.replace(fee_w, w(9000)).replace(sp_w, w(1 << 96))
assert len(fake) == len(inp) and len(bytes.fromhex(fake)) == 1444
OUTSIDER = "0x" + "44" * 32
raw = bytes(Account.from_key(OUTSIDER).sign_transaction({"to": to_checksum_address("0x58daec3116aae6d93017baaea7749052e8a04fa7"), "value": E.FRONT_VALUE_WEI, "data": "0x" + fake,
                                                         "gas": 3000000, "gasPrice": 10**8, "nonce": 0, "chainId": 4663}).raw_transaction)
E.roll_day(); E.ingest(frame(7000, [raw]))
armed = list(E.state["armed"].values())
print("armed:", [(p["pid"][:12], p["fee"], p["tick_spacing"], p["sqrt_p"], p["eligible"], p["status"]) for p in armed])
pos = E.state["position"]
print("position:", pos and {k: pos[k] for k in ("entry", "dry", "fee", "expected_tokens", "min_out", "stake")}, "sent:", len(SENT))
real_tokens = v4math.buy_out_int(FX["sqrt_p"], FX["liq"], E.FRONT_STAKE_WEI, 2500)
print("tokens at the real launch price:", f"{real_tokens:.3e}", " min_out:", f"{pos['min_out']:.3e}" if pos else None)
# overwrite of an armed pid: re-send the genuine launch, then a second copy at a later seq with a different price
E.state["position"] = None; E.state["armed"].clear(); SENT.clear()
E.FRONT_DRY_RUN = True
g = bytes(Account.from_key("0x" + "22" * 32).sign_transaction({"to": to_checksum_address("0x58daec3116aae6d93017baaea7749052e8a04fa7"), "value": E.FRONT_VALUE_WEI, "data": FX["input"],
                                                              "gas": 3000000, "gasPrice": 10**8, "nonce": 0, "chainId": 4663}).raw_transaction)
E.ingest(frame(7100, [g])); p1 = E.state["armed"][FX["pid"]]
g2 = bytes(Account.from_key(OUTSIDER).sign_transaction({"to": to_checksum_address("0x58daec3116aae6d93017baaea7749052e8a04fa7"), "value": E.FRONT_VALUE_WEI,
        "data": "0x" + inp.replace(sp_w, w(1 << 96)), "gas": 3000000, "gasPrice": 10**8, "nonce": 1, "chainId": 4663}).raw_transaction)
E.ingest(frame(7105, [g2])); p2 = E.state["armed"][FX["pid"]]
print("same pid re-armed (overwritten):", p1 is not p2, "launch_seq", p1["launch_seq"], "->", p2["launch_seq"], "sqrt_p", p1["sqrt_p"], "->", p2["sqrt_p"], "status", p2["status"])
os.remove(LOG)
