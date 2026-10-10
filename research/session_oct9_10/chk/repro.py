import os, sys, tempfile
from eth_account import Account
KEY = "0x" + "11" * 32; A = Account.from_key(KEY); RELAY = "0x" + "f1" * 20
LOG = tempfile.mktemp(suffix=".jsonl")
front_on = sys.argv[1]
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": RELAY, "WALLET": A.address.lower(), "PRIVATE_KEY": KEY, "STAKE_ETH": "0.0012",
                   "FRONT": front_on, "FRONT_DRY_RUN": "0", "FRONT_STAKE_ETH": "0.006", "HALT_FILE": LOG + ".halt"})
if len(sys.argv) > 2:  # front already halted
    open(LOG + ".halt.front", "w").write("pulled before front sell\n")
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
def rpc(m, p, tries=4, timeout=10):
    if m == "eth_chainId": return hex(E.CHAIN_ID)
    if m == "eth_getBlockByNumber": return {"baseFeePerGas": hex(20_000_000), "number": "0x1"}
    if m == "eth_getCode": return "0x6000"
    if m == "eth_call":
        d = p[0]["data"][2:]
        return "0x" + (E.POOL_MANAGER[2:] if d == E.SEL_PM else A.address.lower()[2:]).zfill(64)
    if m == "eth_getBalance": return hex(4 * 10**15)   # 0.004 ETH
    if m == "eth_getTransactionCount": return "0x5"
    raise RuntimeError(m)
E.rpc = rpc
class S:
    def __init__(self, u): pass
E.Sender = S
try:
    info = E.checks(); print("STARTED relay_eth", info["relay_eth"], "front_halted", E.state["front_halted"])
except SystemExit as e:
    print("SystemExit:", e, "front_halted", E.state["front_halted"])
