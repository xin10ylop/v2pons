import json, sys, time, importlib.util, os
d = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("results", "/home/user/v2pons/deploy/results.py")
sys.argv = ["results.py", "24"]
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
log = os.path.join(d, "engine.jsonl"); m.LOG = log; m.ENV = os.path.join(d, "none.env"); m.HALT = os.path.join(d, "HALTED")
m.balance = lambda rpc, a: None
t = time.time() - 600
base = {"ev": "trade_done", "dry": False, "fee": 10000, "entry": "seat", "sell_why": "deadline: x"}
evs = [
 {"ev": "start", "t": t, "release": "0.7", "dry_run": False},
 # (a) buy and sell no receipt (RPC down 25 s), what settle logs
 {**base, "t": t+1, "buy": "no receipt", "sell": "no receipt", "eth_in": 0, "eth_out": 0, "gas_wei": 0, "pnl_eth": 0.0, "pnl_usd": 0.0, "ret": None},
 # buy reverted
 {**base, "t": t+2, "buy": {"block": 1, "status": "reverted"}, "sell": {"block": 3, "status": "reverted"}, "eth_in": 0, "pnl_usd": -0.002, "ret": None},
 # (b) pull check failed
 {**base, "t": t+3, "buy": {"block": 100, "status": "ok"}, "sell": {"block": 103, "status": "ok", "tokens_in": 5}, "hold_blocks": 3, "sell_after_buy_blocks": 3, "pull_check": "eth_getLogs: timed out", "eth_in": 10**15, "pnl_usd": -0.15, "ret": -0.06},
 # sell no receipt, buy ok -> sold none halt
 {**base, "t": t+4, "buy": {"block": 200, "status": "ok", "eth_in": 10**15}, "sell": "no receipt", "eth_in": 10**15, "eth_out": 0, "pnl_usd": -2.57, "ret": -1.0},
 # normal: pull none within window
 {**base, "t": t+5, "buy": {"block": 300, "status": "ok"}, "sell": {"block": 303, "status": "ok", "tokens_in": 5}, "hold_blocks": 3, "sell_after_buy_blocks": 3, "pull_after_buy_blocks": None, "pulled_before_sell": False, "eth_in": 10**15, "pnl_usd": 0.1, "ret": 0.04},
]
with open(log, "w") as f:
    for e in evs: f.write(json.dumps(e) + "\n")
open(m.HALT, "w").write("the buy filled and the sell sold none of it (sell: no receipt)")
m.main()
