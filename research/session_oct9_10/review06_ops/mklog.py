import json, time, sys
D = sys.argv[1]; t = time.time() - 3600
ev = []
def L(**k):
    global t; t += 5; k["t"] = t; ev.append(k)
L(ev="start", release="0.6", dry_run=False, entry="follow", max_trades_per_day=6)
for i in range(3):
    pid = "0xp%d" % i
    L(ev="armed", pid=pid, eligible=True, fee=10000)
    L(ev="fire", pid=pid, nonce=10, dry=False, trig_value=10**18)
    L(ev="buy_rejected", pid=pid, reply={"jsonrpc":"2.0","id":1,"error":{"code":-32000,"message":"max fee per gas less than block base fee"}})
    L(ev="nonce", chain=10, engine=10)
pid = "0xp3"
L(ev="armed", pid=pid, eligible=True, fee=10000)
L(ev="fire", pid=pid, nonce=10, dry=False, trig_value=10**18)
L(ev="sell_sent", pid=pid, after_buy=2, why="deadline")
L(ev="alarm", what="settle failed", pid=pid, trace="KeyError: 'effectiveGasPrice'")
L(ev="alarm", what="nonce refresh failed", err="eth_getTransactionCount: timed out")
open(D + "/engine.jsonl", "w").write("".join(json.dumps(e) + "\n" for e in ev))
