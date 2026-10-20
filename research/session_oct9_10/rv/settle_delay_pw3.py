"""How long the slot stays held after a follow trade's receipts are in, old vs new, when eth_getBalance is slow (a timing-out RPC)."""
import os, sys, time, tempfile, importlib.util, json
which = sys.argv[1]
LOG = tempfile.mktemp(suffix=".jsonl")
os.environ.update({"DRY_RUN": "0", "LOG_PATH": LOG, "RELAY": "0x" + "f1" * 20, "WALLET": "0x" + "aa" * 20, "PULL_WATCH_S": "3", "HALT_FILE": LOG + ".halt"})
sys.path.insert(0, "/home/user/v2pons/src")
path = "/home/user/v2pons/src/flip_engine.py" if which == "new" else "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/rv/flip_engine_old.py"
spec = importlib.util.spec_from_file_location("E", path); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
PM = E.POOL_MANAGER; PID = "0x" + "77" * 32
w = lambda x: "%064x" % (x % (1 << 256))
def rec(block, a0, a1):
    return {"status": "0x1", "blockNumber": hex(block), "gasUsed": hex(120000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x3",
            "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, PID, "0x" + w(0)], "data": "0x" + w(a0) + w(a1) + w(0) * 4}]}
R = {"0xb1": rec(100, -E.STAKE_WEI, 10**18), "0xb2": rec(104, int(E.STAKE_WEI * 1.05), -10**18)}
def slow_urlopen_rpc(method, params, tries=4, timeout=10):
    # the real rpc's retry shape, with eth_getBalance hanging to its timeout each try
    if method == "eth_getTransactionReceipt": return R.get(params[0])
    if method == "eth_getLogs": return []
    if method == "eth_getTransactionCount": return "0x9"
    if method == "eth_getBalance":
        for i in range(tries):
            time.sleep(timeout)                     # urlopen timing out
            time.sleep(0.2 * (i + 1))
        raise RuntimeError("eth_getBalance: timed out")
    raise RuntimeError(method)
E.rpc = slow_urlopen_rpc
pos = {"pid": PID, "token": "ab" * 20, "fee": 1134, "entry": "follow", "trig_seq": 98, "trig_value": 1, "nonce": 7, "expected_tokens": 10**18, "min_out": 1, "buy_seq": 100,
       "sell_sent": True, "sell_seq_sent": 102, "buy_hash": "b1", "sell_hash": "b2", "feed_tokens": 10**18, "tp_ret": None, "flat_eth_back": 1, "stake": E.STAKE_WEI, "count_key": "trades_today",
       "pnl_key": "pnl_today_usd", "dry": False}
E.state["position"] = pos; E.state["trades_today"] = 1
t0 = time.monotonic(); E.settle(pos); dt = time.monotonic() - t0
print(f"{which}: slot released {dt:.2f} s after settle started (receipts already in); position None: {E.state['position'] is None}; relay_wei={E.state.get('relay_wei')}")
