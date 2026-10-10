import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import make
V = sys.argv[1]           # results file version
now = time.time(); H = 3600
ENV_OK = "DRY_RUN=0\nRPC_URL=http://127.0.0.1:18545\nWALLET=0x1111111111111111111111111111111111111111\nRELAY=0x2222222222222222222222222222222222222222\nSTAKE_ETH=0.0012\nETH_USD=2570\n"
def start(t, dry=True, rel="0.6", **kw): return {"ev": "start", "release": rel, "dry_run": dry, "entry": "seat", "max_trades_per_day": 3, "halted": None, "t": t, **kw}
sc = {}
# 1 no events at all, no log file, no env
sc["no_events"] = dict(files={}, env=None)
# 1b log exists but empty
sc["empty_log"] = dict(files={"engine.jsonl": []}, env=ENV_OK.replace("18545", "9"))
# 2 only dry-run events
dry = [start(now - 5*H), {"ev": "launch", "tx": "0xab", "seq": 100, "to": "0x3194", "t": now - 4*H},
       {"ev": "armed", "pid": "0xp1", "token": "0xt", "fee": 3000, "eligible": True, "t": now - 4*H + 1},
       {"ev": "armed", "pid": "0xp2", "token": "0xt2", "fee": 10000, "eligible": False, "t": now - 3*H},
       {"ev": "skip", "why": "pool not eligible", "pid": "0xp2", "t": now - 3*H + 5},
       {"ev": "would_fire", "pid": "0xp1", "t": now - 4*H + 2},
       {"ev": "would_sell", "pid": "0xp1", "after_buy": 2, "why": "deadline: no buy behind ours", "tp_ret": None, "t": now - 4*H + 3},
       {"ev": "would_fire", "pid": "0xp3", "t": now - 2*H},
       {"ev": "would_sell", "pid": "0xp3", "after_buy": None, "why": "time fallback", "tp_ret": None, "t": now - 2*H + 1},
       {"ev": "would_sell", "pid": "0xp4", "after_buy": 1, "why": "take profit: a buy behind ours, the sell prices at +6.1%", "tp_ret": 0.061, "t": now - 1*H},
       {"ev": "trade_done", "dry": True, "pid": "0xp1", "t": now - 4*H + 4}]
sc["dry_only"] = dict(files={"engine.jsonl": dry}, env=ENV_OK.replace("DRY_RUN=0", "DRY_RUN=1"))
# 3 live trades with missing fields (older releases)
live = [start(now - 20*H, dry=False, rel="0.2"),
  # 0.2: pull before sell, no pulled_before_sell; ret -1
  {"ev": "trade_done", "dry": False, "route": "relay", "pid": "a", "fee": 3000, "hold_blocks": 6, "pull_after_buy_blocks": 5, "ret": -1.0, "pnl_usd": -3.09, "sell_why": "deadline: x", "t": now - 19*H},
  # 0.2: pull same block, sell first (won)
  {"ev": "trade_done", "dry": False, "route": "relay", "pid": "b", "fee": 3000, "hold_blocks": 5, "pull_after_buy_blocks": 5, "ret": 0.075, "pnl_usd": 0.22, "sell_why": "deadline: x", "t": now - 18*H},
  # buy no receipt: ret None, pnl_usd 0
  {"ev": "trade_done", "dry": False, "pid": "c", "fee": 3000, "buy": "no receipt", "sell": "no receipt", "ret": None, "pnl_usd": 0.0, "t": now - 17*H},
  # buy reverted: ret None, pnl -gas
  {"ev": "trade_done", "dry": False, "pid": "d", "fee": 3000, "buy": {"status": "reverted"}, "sell": {"status": "reverted"}, "ret": None, "pnl_usd": -0.012, "t": now - 16*H},
  # pnl_usd missing entirely, fee missing
  {"ev": "trade_done", "dry": False, "pid": "e", "t": now - 15*H},
  # 0.6 full: pulled_before_sell False, pull later
  {"ev": "trade_done", "dry": False, "entry": "seat", "pid": "f", "fee": 2500, "sell_after_buy_blocks": 3, "hold_blocks": 3, "pull_after_buy_blocks": 9, "pulled_before_sell": False, "ret": 0.071, "pnl_usd": 0.21, "sell_why": "take profit: a buy", "t": now - 14*H},
  # 0.6: pull check failed
  {"ev": "trade_done", "dry": False, "entry": "seat", "pid": "g", "fee": 2500, "sell_after_buy_blocks": 3, "hold_blocks": 3, "pull_check": "eth_getLogs: timed out", "ret": -0.005, "pnl_usd": -0.03, "sell_why": "deadline: x", "t": now - 13*H},
  # 0.6: pulled first, halted
  {"ev": "trade_done", "dry": False, "entry": "follow", "pid": "h", "fee": 2500, "sell_after_buy_blocks": 4, "hold_blocks": 4, "pull_after_buy_blocks": 4, "pulled_before_sell": True, "ret": -1.0, "pnl_usd": -3.1, "sell_why": "deadline: x", "t": now - 12*H},
  {"ev": "alarm", "what": "live trading halted: the operator's pull landed 4 blocks after our buy", "t": now - 12*H + 1},
  # sell no receipt, buy ok: sold none halt
  {"ev": "trade_done", "dry": False, "entry": "seat", "pid": "i", "fee": 2500, "buy": {"status": "ok"}, "sell": "no receipt", "ret": -1.0, "pnl_usd": -3.08, "sell_why": "deadline: x", "t": now - 11*H},
  # pnl_usd None explicitly, ret str?
  {"ev": "trade_done", "dry": False, "pid": "j", "fee": 3000, "pnl_usd": None, "ret": None, "t": now - 10*H},
]
sc["live_old"] = dict(files={"engine.jsonl": live}, env=ENV_OK, halt="the operator's pull landed 4 blocks after our buy, at or before our sell (4): its reaction is now faster than our exit\n")
# 4 rotated logs: .1 plain, .2.gz, .10.gz ; plus older-than-window events
rot = dict(files={
  "engine.jsonl.10.gz": [start(now - 240*H, dry=False), {"ev": "trade_done", "dry": False, "pid": "old", "fee": 3000, "ret": 0.05, "pnl_usd": 0.15, "t": now - 239*H}],
  "engine.jsonl.2.gz": [{"ev": "trade_done", "dry": False, "pid": "r2", "fee": 3000, "ret": 0.05, "pnl_usd": 0.15, "sell_after_buy_blocks": 2, "pull_after_buy_blocks": 8, "pulled_before_sell": False, "t": now - 40*H},
                        {"ev": "trade_done", "dry": False, "pid": "r2b", "fee": 3000, "ret": 0.05, "pnl_usd": 0.15, "sell_after_buy_blocks": 2, "pull_after_buy_blocks": 8, "pulled_before_sell": False, "t": now - 22*H}],
  "engine.jsonl.1": [{"ev": "trade_done", "dry": False, "pid": "r1", "fee": 3000, "ret": -0.006, "pnl_usd": -0.02, "sell_after_buy_blocks": 2, "pull_after_buy_blocks": None, "pulled_before_sell": False, "t": now - 10*H}],
  "engine.jsonl": [{"ev": "flow", "seq": 1, "t": now - 60}]}, env=ENV_OK)
sc["rotated"] = rot
# 5 live engine running for 3 days: start event outside the 24h window
sc["live_long_running"] = dict(files={"engine.jsonl.2.gz": [start(now - 72*H, dry=False, rel="0.7", entry="auto", max_trades_per_day=10)],
                                      "engine.jsonl": [{"ev": "flow", "seq": 1, "t": now - 60},
                                                       {"ev": "trade_done", "dry": False, "entry": "follow", "pid": "x", "fee": 3000, "ret": 0.024, "pnl_usd": 0.07, "sell_after_buy_blocks": 3, "pull_after_buy_blocks": None, "pulled_before_sell": False, "sell_why": "take profit: x", "t": now - 2*H}]},
                             env=ENV_OK)
# 6 empty HALTED file
sc["halt_empty"] = dict(files={"engine.jsonl": [start(now - H, dry=False)]}, env=ENV_OK, halt="")
# 7 junk lines: non-dict json, missing ev, binary garbage
sc["junk"] = dict(files={"engine.jsonl": [start(now - H, dry=False), "null", "[1,2]", "5", '{"t": %f}' % (now - 10), '{"ev":"flow","seq":1', "\x00\x00\x00" + json.dumps({"ev": "flow", "t": now - 5})]}, env=ENV_OK)
# 8 rpc variants
for port, nm in ((9, "rpc_refused"), (18546, "rpc_hang"), (18547, "rpc_err"), (18548, "rpc_html")):
    sc[nm] = dict(files={"engine.jsonl": [start(now - H, dry=False)]}, env=ENV_OK.replace("18545", str(port)))
sc["rpc_dns"] = dict(files={"engine.jsonl": [start(now - H, dry=False)]}, env=ENV_OK.replace("http://127.0.0.1:18545", "https://rpc.invalid.example"))
# 9 env with quotes / inline comments / spaces
sc["env_quoted"] = dict(files={"engine.jsonl": [start(now - H, dry=False)]}, env='WALLET="0x1111111111111111111111111111111111111111"\nRELAY = 0x2222222222222222222222222222222222222222   # the relay\nRPC_URL=http://127.0.0.1:18545\n')
for name, kw in sc.items():
    make(name, V, kw["files"], kw.get("env"), kw.get("halt"))
print(" ".join(sc))
