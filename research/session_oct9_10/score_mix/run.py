import json, sys, time, os
sys.path.insert(0, "/home/user/v2pons/src")
import score, v4math
Q96 = 1 << 96
FX = json.load(open("/home/user/v2pons/tests/data/front_launch.json"))
SP, LQ, FEE = FX["sqrt_p"], FX["liq"], 2500
now = time.time()
ev = [{"t": now - 100, "ev": "start", "hold_blocks": 4, "sell_lead_blocks": 2, "take_profit": 0.01, "stake_eth": 0.0012,
       "front": True, "front_dry_run": True, "front_hold_blocks": 12, "front_stake_eth": 0.0012}]
SWAPS = {}
def after(sp, eth):  # sqrtP after a buy of eth (net of fee)
    return int(Q96 / (Q96 / sp + eth * (1 - FEE / 1e6) / LQ))
# 2 follow trades: launch L, crowd first buy +45 (trigger), our buy lands trig+2, crowd keeps buying at trig+3
for i in range(2):
    pid = "0x" + ("f%d" % i) * 32; L = 1000 + i * 100; trig = L + 45
    ev += [{"t": now - 90, "ev": "armed", "pid": pid, "fee": FEE, "sqrt_p": SP, "liq": LQ, "seq": L, "eligible": True, "entry": "follow"},
           {"t": now - 89, "ev": "first_buy", "pid": pid, "seq": trig, "offset": 45, "value": int(0.05e18)},
           {"t": now - 88, "ev": "fire", "pid": pid, "trig_seq": trig, "buy_hash": "ab" * 32, "entry": "follow"}]
    s1 = after(SP, 0.05e18); s2 = after(s1, 0.05e18)
    SWAPS[pid] = ([(trig, 0, -int(0.05e18), 1, s1, LQ, "0x01"), (trig + 3, 0, -int(0.05e18), 1, s2, LQ, "0x02")], None)
# 8 front dry decisions: launch L, would_fire at L (trig_seq = launch), the volume bot's first buy at L+9 for 0.12 ETH
for i in range(8):
    pid = "0x" + ("e%d" % i) * 32; L = 5000 + i * 100
    ev += [{"t": now - 80, "ev": "armed", "pid": pid, "fee": FEE, "sqrt_p": SP, "liq": LQ, "seq": L, "eligible": True, "entry": "front", "launcher_code": "front"},
           {"t": now - 79, "ev": "would_fire", "pid": pid, "trig_seq": L, "entry": "front", "stake": int(0.0012e18), "send_after": 12, "tp": 0.01},
           {"t": now - 78, "ev": "first_buy", "pid": pid, "seq": L + 9, "offset": 9, "value": int(0.12e18)}]
    SWAPS[pid] = ([(L + 9, 0, -int(0.12e18), 1, after(SP, 0.12e18), LQ, "0x03")], None)
calls = []
def fake_pool_events(pid, b0, span=600):
    calls.append(pid); return SWAPS[pid]
score.pool_events = fake_pool_events
p = os.path.join(os.path.dirname(__file__), "engine.jsonl"); open(p, "w").write("\n".join(json.dumps(e) for e in ev) + "\n")
sys.argv = ["score.py", p, "1"]; score.main()
print("\neth_getLogs calls:", len(calls), "front:", sum(1 for c in calls if c.startswith("0xe")))
# what front's own exit would price: our buy at L+1, sell on the bot's buy (+9), landing 2 later -> hold 12 path
pf = score.price(SWAPS["0x" + "e0" * 32][0], None, SP, LQ, FEE, 5001, 12, 0, 0.01, int(0.0012e18))
print("front with its own exit (hold 12, lead 0):", pf)
