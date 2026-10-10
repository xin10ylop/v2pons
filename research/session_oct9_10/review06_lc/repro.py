import os, sys, json, time, tempfile
from eth_account import Account
from eth_utils import keccak
LOG = tempfile.mktemp(suffix=".jsonl")
os.environ.update({"DRY_RUN": "1", "LOG_PATH": LOG, "LAUNCHERS": "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "ENTRY": "seat", "LAUNCH_SELECTORS": "2fcb9108"})
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mod"))
import flip_engine as E
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
FRESH = "0x" + "5e" * 20; OP_CODE = "0x" + "60806040" * 50; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}
PID = "0x" + "77" * 32; TOKEN = "0x" + "ab" * 20
def launch_receipt(h):
    init = {"address": E.POOL_MANAGER, "topics": ["0x" + E.T_INIT, PID, "0x" + "0" * 64, "0x" + w(TOKEN)],
            "data": "0x" + w(1134) + w(60) + w(0) + w(1292187213925453985058262482146976) + w(194000)}
    ml = {"address": E.POOL_MANAGER, "topics": ["0x" + E.T_ML, PID, "0x" + w(0)], "data": "0x" + w(-887220) + w(887220) + w(61_310_000_000_000_000_000_000) + w(0)}
    return {"status": "0x1", "logs": [init, ml], "blockNumber": "0x10"}
def run(code_lag_s, rcpt_lag_s, code_429=False):
    t0 = time.monotonic()
    def fake_rpc(method, params, tries=4, timeout=10):
        if method == "eth_getTransactionReceipt": return launch_receipt(params[0]) if time.monotonic() - t0 >= rcpt_lag_s else None
        if method == "eth_getCode":
            if code_429:   # what rpc() does after 'tries' 429 replies
                time.sleep(0.2 + 0.4); raise RuntimeError("eth_getCode: HTTP Error 429: Too Many Requests")
            return "0x" if time.monotonic() - t0 < code_lag_s else OP_CODE
        raise RuntimeError(method)
    E.rpc = fake_rpc; E.state["armed"].clear()
    E.arm_launch("0x" + "aa" * 32, 1000, int(time.time()), t0, FRESH[2:] if False else FRESH.replace("0x", ""))
    p = E.state["armed"].get(PID)
    return {"arm_ms": p and p["arm_ms"], "eligible": p and p["eligible"], "launcher_code": p and p["launcher_code"]}
print("A backend in sync (code and receipt at once):          ", run(0.0, 0.05))
print("B backend lagging 150 ms (code '0x' until then):       ", run(0.15, 0.16))
print("C getCode answered 429 twice:                         ", run(0.0, 0.05, code_429=True))
