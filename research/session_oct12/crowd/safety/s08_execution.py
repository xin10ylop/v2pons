"""Execution of a v3crowd buy as the engine sends it (src/flip_engine.py: fired at the end of the launch block's feed message, minOut = the
launch-state quote x (1 - BUY_SLIP 0.03), deadline the launch block's time + BUY_DEADLINE_S 3 s, landing about + 2), from the replay's per-launch
rows (../replay/r06_rows.json: every buy before the crowd's first, with its block offset) and the reaction check's records:
(1) what lands ahead of a + 1 / + 2 buy (blocks + 0..+ 1, and + 2 if ordered before ours): ETH, who; our fill against the minOut (a ratio under
0.97 = TooLittleOut, the buy reverts, gas only); (2) the crowd's first real buy at or before + 2 (we would land behind it); (3) the time the
launch block leaves for a 3 s deadline (block timestamps: blocks per second); (4) the streak halt (FRONT_NONBOT_HALT 8 on the box: 8 live trades
in a row under +2% net halt the family) and V3_DAILY_STOP_USD (10) on the replay's chronological returns at 0.002 and 0.004 ETH;
(5) the slot a live v3crowd trade holds (from the fire to both receipts) per day. Writes s08_execution.out."""
from common import *
import collections, statistics as stt
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
from v3dec import sqrt_at_tick
D = json.load(open(os.path.join(HERE, "..", "replay", "r06_rows.json"))); R = sorted(D["rows"], key=lambda r: r["ts"])
ETH = json.load(open(J("s00_probe.json")))["eth_usd"]
print(f"replay rows {len(R)} (WETH token0 launches {utc(R[0]['ts'])} .. {utc(R[-1]['ts'])}); ETH ${ETH:,.2f}")
# (1) ahead of our buy
for land in (1, 2):
    for q in (0.002, 0.004):
        ratios = []; ahead_eth = []; who = collections.Counter(); rev = 0
        for r in R:
            sp = sqrt_at_tick(r["hi"]); L = r["L"]
            ahead = [b for b in r["before"] if b[0] < land]
            a = sum(b[4] for b in ahead); ahead_eth.append(a)
            for b in ahead: who[(b[2] or "?")[:10]] += 1
            q0 = v4math.buy_out_int(sp, L, int(q * 1e18), 100)
            sp1 = int(v4math.sqrt_after_buy(sp, L, int(a * 1e18) * (10 ** 6 - 100) // 10 ** 6)) if a else sp
            q1 = v4math.buy_out_int(sp1, L, int(q * 1e18), 100)
            ratios.append(q1 / q0); rev += q1 < 0.97 * q0
        print(f"(1) our buy landing + {land}, {q} ETH: pools with buys ahead {sum(1 for a in ahead_eth if a > 0)}/{len(R)}; ETH ahead p50/p90/max "
              f"{pct(ahead_eth, .5):.5f}/{pct(ahead_eth, .9):.5f}/{max(ahead_eth):.5f}; fill / launch quote min {min(ratios):.4f} p10 {pct(ratios, .1):.4f}; "
              f"under the 0.97 minOut (reverts) {rev}; who ahead {who.most_common(4)}")
# the same-block case: buys at + 2 (ours lands at + 2: before or after them by the sequencer's order)
at2 = [(r["pool"], b) for r in R for b in r["before"] if b[0] == 2]
print(f"    buys in block + 2 itself (a race with ours): {len(at2)} in {len(set(p for p, _ in at2))} pools; ETH max {max([b[4] for _, b in at2] or [0]):.5f}; who {collections.Counter((b[2] or '?')[:10] for _, b in at2).most_common(3)}")
# (2) the crowd's first real buy early
c1 = [r["crowd1_off"] for r in R if r["crowd1_off"] is not None]; e1 = [r["eng1_off"] for r in R if r.get("eng1_off") is not None]
print(f"(2) the crowd's first real buy at + 0..+ 2 (ahead of or racing our + 2 buy): {sum(o <= 2 for o in c1)}; at + 3..+ 5: {sum(3 <= o <= 5 for o in c1)}; "
      f"the engine's first trigger (any >= 0.005 ETH) at <= + 2: {sum(o <= 2 for o in e1)}; median {stt.median(c1):.0f}")
# (4) the streak halt and the V3 day stop, chronological
for q in ("0.002", "0.004"):
    key = f"{q}|2|2"; rets = [r["r"][key]["ret"] for r in R]
    paid = [x >= 0.02 for x in rets]
    streak = 0; halts = []; longest = 0; trades_to_halt = []
    for i, ok in enumerate(paid):
        streak = 0 if ok else streak + 1; longest = max(longest, streak)
        if streak == 8: halts.append(i); streak = 0
    # from each start point: trades until the 8th in a row under +2%
    for s in range(len(paid)):
        k = 0; n = 0
        for ok in paid[s:]:
            n += 1; k = 0 if ok else k + 1
            if k == 8: trades_to_halt.append(n); break
    hrs = [(R[min(s + n - 1, len(R) - 1)]["ts"] - R[s]["ts"]) / 3600 for s, n in enumerate(trades_to_halt)]
    print(f"(4) {q} ETH (${float(q) * ETH:.2f}): trades paying >= +2% net {sum(paid)}/{len(paid)} ({sum(paid) / len(paid):.0%}); longest run under +2% {longest}; "
          f"halts (8 in a row, restarted each time) {len(halts)} in {len(R)} launches; from a random start the halt comes after p25/50/75 "
          f"{pct(trades_to_halt, .25):.0f}/{pct(trades_to_halt, .5):.0f}/{pct(trades_to_halt, .75):.0f} trades ({pct(hrs, .5):.1f} h median); never in {len(paid) - len(trades_to_halt)} start points")
    day = collections.defaultdict(float); worst = collections.defaultdict(float)
    for r in R:
        d = time.strftime("%m-%d", time.gmtime(r["ts"])); day[d] += r["r"][key]["ret"] * float(q) * ETH; worst[d] = min(worst[d], day[d])
    print(f"    V3 day ($, cumulative, UTC days): end {dict((k, round(v, 2)) for k, v in day.items())}; lowest point {dict((k, round(v, 2)) for k, v in worst.items())}")
# (5) the slot: from the fire (launch block) to both receipts: the sell lands at min(trigger + 20, + 80); receipts ~0.5 s after
bps = 9.70
holds = []
for r in R:
    trig = r.get("eng1_off")
    sell = min(trig + 20, 80) if trig is not None and trig >= 2 else 80
    holds.append(sell)
per_day = len(R) / ((R[-1]["ts"] - R[0]["ts"]) / 86400)
print(f"(5) blocks from the launch to our sell landing p50 {stt.median(holds):.0f} (mean {stt.mean(holds):.1f}); at {bps} blocks/s that is {stt.mean(holds) / bps:.1f} s + ~1 s for the receipts "
      f"(wait_receipt polls every 40 ms) = ~{stt.mean(holds) / bps + 1:.0f} s a trade; {per_day:.0f} launches a day -> the slot held {per_day * (stt.mean(holds) / bps + 1) / 864:.2f}% of the day; "
      f"the V3 pull check after it (PULL_WATCH_S 3 s + getLogs) holds only the next V3 fire")
