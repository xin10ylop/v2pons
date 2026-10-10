import json, os, sys, time, importlib.util
CASE = sys.argv[1] if len(sys.argv) > 1 else "a"
D = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("R", "/home/user/v2pons/deploy/results.py"); sys.argv = ["results.py", "24"]
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
R.LOG = D + "/engine.jsonl"; R.ENV = D + "/engine.env"; R.HALT = D + "/HALTED"
R.balance = lambda rpc, a: 0.0014 if a.startswith("0xab") else None
now = time.time()
ev = [
 {"ev": "start", "release": "0.5", "dry_run": False, "entry": "seat", "max_trades_per_day": 1, "t": now - 40 * 3600},
 {"ev": "armed", "eligible": True, "entry": "follow", "t": now - 3600},
 {"ev": "armed", "eligible": True, "entry": "seat", "t": now - 3500},
 {"ev": "fire", "pid": "0xa", "nonce": 27, "fee": 1600, "entry": "seat", "t": now - 3000},
 {"ev": "buy_rejected", "pid": "0xa", "reply": {"error": {"code": -32000, "message": "insufficient funds for gas * price + value"}}, "t": now - 2999},
 {"ev": "fire", "pid": "0xb", "nonce": 27, "fee": 890, "entry": "follow", "t": now - 2000},
 {"ev": "trade_done", "nonce": 27, "fee": 890, "entry": "follow", "ret": 0.024, "pnl_usd": 0.07, "sell_after_buy_blocks": 3, "pull_after_buy_blocks": None, "pulled_before_sell": False, "buy": {"status": "ok"}, "sell": {"status": "ok"}, "sell_why": "take profit: x", "t": now - 1990},
 {"ev": "fire", "pid": "0xc", "nonce": 29, "fee": 890, "entry": "follow", "t": now - 1500},
 {"ev": "trade_done", "nonce": 29, "fee": 890, "entry": "follow", "ret": None, "pnl_usd": -0.001, "buy": "no receipt", "sell": "no receipt", "sell_why": "deadline: y", "t": now - 1400},
 {"ev": "fire", "pid": "0xd", "nonce": 29, "fee": 890, "entry": "follow", "t": now - 1000},
 {"ev": "trade_done", "nonce": 29, "fee": 890, "ret": None, "pnl_usd": -0.002, "buy": {"status": "reverted"}, "sell": {"status": "reverted"}, "sell_why": "deadline: y", "t": now - 990},
 {"ev": "fire", "pid": "0xe", "nonce": 31, "fee": 890, "entry": "follow", "t": now - 900},
 {"ev": "trade_done", "nonce": 31, "fee": 890, "ret": -0.01, "pnl_usd": -0.03, "sell_after_buy_blocks": 3, "pull_after_buy_blocks": 2, "buy": {"status": "ok"}, "sell": {"status": "ok"}, "sell_why": "deadline: y", "t": now - 890},
 {"ev": "fire", "pid": "0xf", "nonce": 33, "fee": 890, "entry": "follow", "t": now - 600},
 {"ev": "trade_done", "nonce": 32, "fee": 890, "ret": 0.01, "pnl_usd": 0.01, "sell_after_buy_blocks": 3, "pull_check": "timeout", "buy": {"status": "ok"}, "sell": {"status": "ok"}, "sell_why": "deadline: y", "t": now - 5000},
 {"ev": "alarm", "what": "nonce refresh failed", "t": now - 500},
 {"ev": "flow", "halted": "the operator's pull landed 2 blocks after our buy", "t": now - 60},
]
case = CASE
open(R.LOG, "w").write("\n".join(json.dumps(e) for e in ev) + "\n")
open(R.ENV, "w").write("DRY_RUN=0\nWALLET=0xab5a\nRELAY=0x2abb\nSTAKE_ETH=0.0012  # x\nETH_USD=2400\n")
if os.path.exists(R.HALT): os.remove(R.HALT)
if case == "b": open(R.HALT, "w").write("")
if case == "c": open(R.LOG, "w").write("")
R.main()
