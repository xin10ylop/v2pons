#!/usr/bin/env python3
"""The live trades, read back from the chain: every buy and sell a wallet made on the operator's launches in a window, with the
operator's crowd around it, the liquidity pull, and the trade repriced as if the sell had landed in each block after the buy.

The first seven live trades (Oct 8, 13:15-13:20 UTC, $3 each through FlipRelay) were four wins and three -100% losses. Read from
this angle the losses are not a mystery: the operator pulled the liquidity 5-13 blocks after every one of our buys, and the only
difference between a win and a loss was whether our sell landed before the pull. The money in every win came from the operator's
crowd buys already on their way when we bought (landing 1-3 blocks behind ours); after them the crowd stops. The rule this leads
to (release 0.3 of the engine): sell on the first buy behind ours that pays, and in any case land by our buy + 4.

    python3 research/live_trades.py 0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8 "2026-10-08 11:30" "2026-10-08 15:00" > research/data/live_trades_oct8.txt

The wallet's swaps are found by the transaction's sender (the router route) or by the relay it deployed (the relay route: the
Swap event's sender). Public RPC only. Section 4 checks the reading against the operator's other launches in the same window.
"""
import json, sys, time, calendar, collections, urllib.request, urllib.error, os
from eth_utils import keccak
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import v4math
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "8876789976decbfcbbbe364623c63652db8c0904"; OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
ETHUSD = 2570.0; HOLD, LEAD, TP = 4, 2, 0.01                                  # the engine's release 0.3 exit
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
def post(body):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e: time.sleep(4 * (i + 1) if e.code == 429 else 2)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc gave up")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]
def batch(calls):
    out = []
    for i in range(0, len(calls), 50):
        r = sorted(post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(calls[i:i+50])]), key=lambda x: x["id"])
        out += [x.get("result") for x in r]
    return out
def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)
def block_at(ts):
    lo, hi = 1, int(rpc("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo + hi) // 2
        if int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
    return lo


def main():
    wallet = sys.argv[1].lower().replace("0x", "")
    t_lo, t_hi = (calendar.timegm(time.strptime(a, "%Y-%m-%d %H:%M")) for a in sys.argv[2:4])
    b_lo, b_hi = block_at(t_lo), block_at(t_hi)
    inits = []
    for a in range(b_lo, b_hi, 99999):
        inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 99998, b_hi))
    pools = {}
    for l, t in zip(inits, batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])):
        if t and (t.get("to") or "")[2:].lower() == OP:
            d = l["data"]; pools[l["topics"][1]] = {"bn": int(l["blockNumber"], 16), "token": l["topics"][3][-40:], "fee": W(d, 0), "sqrtP0": W(d, 3), "tick0": sgn(W(d, 4)), "deployer": t["from"][2:].lower()}
    pids = sorted(pools, key=lambda p: pools[p]["bn"]); ev = collections.defaultdict(list)
    for i in range(0, len(pids), 60):
        bt = pids[i:i+60]; lo = min(pools[p]["bn"] for p in bt); hi = max(pools[p]["bn"] for p in bt) + 12000
        for a in range(lo, hi, 99999):
            for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 99998, hi)): ev[l["topics"][1]].append(l)
    hashes = sorted({l["transactionHash"] for p in pids for l in ev[p]})
    T = dict(zip(hashes, batch([("eth_getTransactionByHash", [h]) for h in hashes])))
    bts = dict(zip(pids, batch([("eth_getBlockByNumber", [hex(pools[p]["bn"]), False]) for p in pids])))
    print(f"wallet 0x{wallet}; window {sys.argv[2]} - {sys.argv[3]} UTC (blocks {b_lo}-{b_hi}); {len(pids)} launches by the operator 0x{OP[:10]}\n")

    rows = []; mine = set()
    for pid in pids:
        p = pools[pid]; ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
        sw = []
        for l in ls:
            if l["topics"][0] != T_SWAP: continue
            t = T[l["transactionHash"]]
            sw.append({"bn": int(l["blockNumber"], 16), "idx": int(t["transactionIndex"], 16), "a0": s128(W(l["data"], 0)), "a1": s128(W(l["data"], 1)), "sp": W(l["data"], 2), "L": W(l["data"], 3),
                       "ours": t["from"][2:].lower() == wallet, "via": "router" if l["topics"][2][-40:] == UR else "0x" + l["topics"][2][-40:][:8]})
        pulls = sorted((int(l["blockNumber"], 16), int(T[l["transactionHash"]]["transactionIndex"], 16)) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
        rows.append((pid, p, sw, pulls[0] if pulls else None))
        if any(x["ours"] for x in sw): mine.add(pid)

    print("1. THE TRADES (blocks are ~0.1 s; 'after buy' counts blocks from our buy's block)")
    print("   #  time      route   fee      trigger  our buy   return   pull after buy  sell landed  pulled first  buys behind ours, 20 blocks (block: ETH)")
    trades = []
    for pid, p, sw, pull in rows:
        if pid not in mine: continue
        ours = [x for x in sw if x["ours"]]; buy, sell = ours[0], (ours[1] if len(ours) > 1 else None); B = buy["bn"]
        real = [x for x in sw if x["a0"] <= -2e14 and not x["ours"]]; trig = real[0]["bn"] if real else None
        ret = (sell["a0"] + buy["a0"]) / -buy["a0"] if sell else None
        behind = [x for x in sw if not x["ours"] and x["a0"] < 0 and (x["bn"], x["idx"]) > (buy["bn"], buy["idx"]) and (pull is None or (x["bn"], x["idx"]) < pull) and x["bn"] - B <= 20]
        first = pull is not None and sell is not None and pull < (sell["bn"], sell["idx"])
        n = len(trades) + 1; trades.append((n, pid, p, sw, pull, buy, sell, B, ret))
        print(f"   {n}  {time.strftime('%H:%M:%S', time.gmtime(int(bts[pid]['timestamp'], 16)))}  {'router' if buy['via'] == 'router' else 'relay ':6s}  {p['fee']/1e4:.4f}%  +{trig - p['bn'] if trig else '-':<4}     trig+{B - trig if trig else '?'}    "
              f"{ret:+7.1%}  {pull[0] - B if pull else '-':>6}          {sell['bn'] - B if sell else '-':>4}         {'YES' if first else 'no ':3s}           "
              + (", ".join(f"+{x['bn'] - B}: {-x['a0'] / 1e18:.4f}" for x in behind) or "none"))
    rs = [t[8] for t in trades if t[8] is not None]
    print(f"   {len(rs)} trades: {sum(1 for r in rs if r > 0)} positive, {sum(1 for r in rs if r <= -0.99)} at -100%; mean {sum(rs) / len(rs):+.1%}. Every -100% is a sell that landed after the pull.")
    for n, pid, p, sw, pull, buy, sell, B, ret in trades:
        if sell and 0 < -sell["a1"] < buy["a1"]:
            print(f"   trade {n} sold {-sell['a1'] / buy['a1']:.1%} of what it bought ({-sell['a1']:.4e} of {buy['a1']:.4e}; the buy's minOut, its receipt not in yet): the rest stayed in the wallet")
    print()

    print("2. THE SAME TRADES, SOLD IN EACH BLOCK AFTER THE BUY (all the tokens bought, priced after every other swap in the blocks")
    print("   before the landing, net of the two swaps' gas; X: the pull landed in an earlier block, =: the pull's own block, a race")
    print("   decided by arrival order)")
    print("   #   " + "  ".join(f"  +{k}  " for k in range(1, 8)))
    rule = []
    gas = 2 * 110_000 * 0.0201e9
    for n, pid, p, sw, pull, buy, sell, B, ret in trades:
        fee = p["fee"]; tok = buy["a1"]; eth_in = -buy["a0"]
        def at(k):
            if pull is not None and pull[0] < B + k: return None, "   X   "
            prev = [x for x in sw if not x["ours"] and (x["bn"], x["idx"]) > (buy["bn"], buy["idx"]) and x["bn"] <= B + k - 1]
            sp, L = (prev[-1]["sp"], prev[-1]["L"]) if prev else (buy["sp"], buy["L"])
            r = (v4math.sell_out_int(sp, L, tok, fee) - eth_in - gas) / eth_in
            return r, (f"{r:+6.1%} " if pull is None or pull[0] > B + k else f"={r:+5.1%} ")
        print(f"   {n}  " + " ".join(at(k)[1] for k in range(1, 8)))
        # release 0.3: the sell is sent in the feed block of the first buy behind ours that pays TP (at the latest B + HOLD - LEAD)
        # and lands one or two blocks later; the slow case (two) is the one counted
        send = HOLD - LEAD
        for x in sw:
            if x["ours"] or x["a0"] >= 0 or (x["bn"], x["idx"]) <= (buy["bn"], buy["idx"]) or x["bn"] - B > HOLD - LEAD: continue
            r_now = (v4math.sell_out_int(x["sp"], x["L"], tok, fee) - eth_in - gas) / eth_in
            if r_now >= TP: send = x["bn"] - B; break
        r_fast, r_slow = at(send + 1)[0], at(send + 2)[0]
        rule.append((n, send, r_fast, r_slow))
    print(f"\n3. THE RELEASE 0.3 EXIT ON THE SAME TRADES: sell in the feed block of the first buy behind ours that prices the sell at +{TP:.0%}")
    print(f"   or better, at the latest when the feed shows our buy + {HOLD - LEAD}; it lands one or two blocks after it was sent")
    for n, send, r_fast, r_slow in rule:
        f = lambda r: "-100% (pull first)" if r is None else f"{r:+.1%}"
        print(f"   {n}: sent at +{send} ({'take profit' if send < HOLD - LEAD or (send == HOLD - LEAD and r_fast is not None and r_fast >= TP) else 'deadline'}), landing +{send + 1}: {f(r_fast)}, landing +{send + 2}: {f(r_slow)}")
    slow = [r if r is not None else -1.0 for _, _, _, r in rule]
    print(f"   landing late (the slow case) on all {len(slow)}: mean {sum(slow) / len(slow):+.1%}, {sum(1 for r in slow if r > 0)} positive, worst {min(slow):+.1%}; "
          f"as traded: mean {sum(rs) / len(rs):+.1%}, worst {min(rs):+.1%}\n")

    print("4. IS THE PULL A REACTION TO US? The operator's launches in the same window, by who bought them (pull = the first liquidity")
    print("   removal; 'first buy' = the first real-size buy, 0.0002 ETH or more)")
    for pid, p, sw, pull in rows:
        real = [x for x in sw if x["a0"] <= -2e14]; first = real[0]["bn"] if real else None
        tag = "OURS " if pid in mine else ("     " if all(x["via"] == "router" for x in sw) else "other")
        gap = (pull[0] - first) if pull and first else None
        print(f"   {time.strftime('%H:%M:%S', time.gmtime(int(bts[pid]['timestamp'], 16)))} {tag} fee {p['fee']/1e4:7.4f}%  first buy +{first - p['bn'] if first else '-':<4}  pull {('%d blocks (%.0f s) after it' % (gap, gap * 0.103)) if gap is not None else ('at +%d' % (pull[0] - p['bn']) if pull else 'none in 20 min'):28s}  "
              f"buys before the pull {sum(1 for x in real if pull is None or (x['bn'], x['idx']) < pull)}")
    print("   (blocks to seconds at 0.103 s a block, measured over the window)")


main()
