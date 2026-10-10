"""A follow launch whose arming thread cannot start: its hash stays in state['arming'] for the run, and every live front fire is skipped."""
import os, sys, json, time, tempfile, threading, base64
LOG = tempfile.mktemp(suffix=".jsonl")
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": "0x" + "f1" * 20, "WALLET": "0x" + "aa" * 20, "HALT_FILE": LOG + ".halt", "FRONT": "1", "FRONT_DRY_RUN": "0"})
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
from eth_account import Account
from eth_utils import to_checksum_address
E.rpc = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no rpc"))
def signed(key, to, value, data, nonce):
    return bytes(Account.from_key(key).sign_transaction({"to": to_checksum_address(to), "value": value, "data": data, "gas": 300000, "gasPrice": 10 ** 8, "nonce": nonce, "chainId": 4663}).raw_transaction)
def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})
real_start = threading.Thread.start
def start(self):
    if getattr(self, "_target", None) is E.arm_launch_thread:
        raise RuntimeError("can't start new thread")
    return real_start(self)
threading.Thread.start = start
launcher = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
E.ingest(frame(100, [signed("0x" + "22" * 32, launcher, 0, "0x2fcb9108" + "00" * 32, 0)]))
threading.Thread.start = real_start
print("arming after the failed start:", E.state["arming"])
# a live front pool, fully eligible, at launch + 0: _fire's front-yield gate
p = {"pid": "0x" + "55" * 32, "token": "cd" * 20, "fee": 2500, "tick_spacing": 50, "hooks": "0" * 40, "c0": "0" * 40, "sqrt_p": E.FRONT_SQRT_P, "liq": E.FRONT_LIQ, "sp": float(E.FRONT_SQRT_P),
     "launch_seq": 5000, "eligible": True, "entry": "front", "status": "armed", "first_buy": None, "tx": "ff"}
E.state["seq"] = 5000; E.state["nonce"] = 1; E._fire(p, 5000, 0, 0, "ff", time.monotonic(), 5000)
print("front fire 4900 blocks later:", [json.loads(l).get("why") for l in open(LOG) if '"skip"' in l][-1], "| position:", E.state["position"])
