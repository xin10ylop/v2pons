import json, os, sys, time, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("R", "/home/user/v2pons/deploy/results.py"); sys.argv = ["results.py", "24"]
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
R.LOG = D + "/engine2.jsonl"; R.ENV = D + "/engine2.env"; R.HALT = D + "/HALTED2"
R.balance = lambda rpc, a: 0.002
now = time.time()
ev = [{"ev": "start", "release": "0.9", "dry_run": False, "entry": "auto", "max_trades_per_day": 100, "front": True, "front_dry_run": True, "front_stake_eth": 0.0012, "front_max_per_day": 400, "t": now - 3600},
      {"ev": "fire", "pid": "0xa", "nonce": 40, "fee": 1500, "entry": "follow", "t": now - 3000},
      {"ev": "trade_done", "nonce": 40, "fee": 1500, "entry": "follow", "ret": 0.05, "pnl_usd": 0.15, "sell_after_buy_blocks": 3, "pull_after_buy_blocks": None, "pulled_before_sell": False, "buy": {"status": "ok"}, "sell": {"status": "ok"}, "sell_why": "take profit: x", "t": now - 2990}]
for i in range(12):
    ev.append({"ev": "would_fire", "pid": f"0xf{i}", "entry": "front", "t": now - 2000 + i * 60})
    ev.append({"ev": "would_sell", "pid": f"0xf{i}", "after_buy": 8, "why": "take profit: x" if i % 4 else "deadline: y", "tp_ret": 0.12 + i / 100 if i % 4 else None, "t": now - 1999 + i * 60})
open(R.LOG, "w").write("\n".join(json.dumps(e) for e in ev) + "\n")
open(R.ENV, "w").write("DRY_RUN=0\nWALLET=0xab\nRELAY=0xcd\nFRONT=1\n")
for p in (R.HALT, R.HALT + ".front"):
    if os.path.exists(p): os.remove(p)
if len(sys.argv) > 1 and os.environ.get("FH"): open(R.HALT + ".front", "w").write("the operator's pull landed 5 blocks after our buy")
R.main()
