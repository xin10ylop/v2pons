import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk import make
now = time.time(); H = 3600
ENV = "DRY_RUN=0\nRPC_URL=http://127.0.0.1:18545\nWALLET=0x1111111111111111111111111111111111111111\nRELAY=0x2222222222222222222222222222222222222222\nSTAKE_ETH=0.0012\n"
ev = [{"ev": "start", "release": "0.7", "dry_run": False, "entry": "auto", "max_trades_per_day": 10, "t": now - 5*H}]
for i in range(3):
    ev += [{"ev": "armed", "pid": f"p{i}", "fee": 3000, "eligible": True, "t": now - 4*H + i*600},
           {"ev": "fire", "pid": f"p{i}", "fee": 3000, "t": now - 4*H + i*600 + 30},
           {"ev": "buy_rejected", "pid": f"p{i}", "reply": {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "insufficient funds for gas * price + value: balance 1200, tx cost 105000000000"}}, "t": now - 4*H + i*600 + 30}]
# a trade whose settle failed, then a later unrelated alarm
ev += [{"ev": "armed", "pid": "q", "fee": 3000, "eligible": True, "t": now - 2*H},
       {"ev": "fire", "pid": "q", "fee": 3000, "t": now - 2*H + 30},
       {"ev": "sell_sent", "pid": "q", "t": now - 2*H + 31},
       {"ev": "alarm", "what": "settle failed", "pid": "q", "t": now - 2*H + 60},
       {"ev": "alarm", "what": "nonce refresh failed", "err": "timed out", "t": now - 2*H + 61}]
make("rejected", sys.argv[1], {"engine.jsonl": ev}, ENV)
