"""Where the follow trade's gain comes from (80-pool fully attributed sample, v07): flows by class in our holding window [a, b) with
a = trigger + 2, b = a + 60, and counterfactual replays keeping only the bot's swaps or only the others'. The bot's own sells: count,
timing after its first buy, size. Classes: bot = tx to 0xd6d35b56; launch = tx from the launch wallet; other = the rest."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
samp = json.load(open(os.path.join(V, "sample_pools.json")))
crowd = {t["from"] for t in T.values() if t.get("to") == BOT}
Q = int(0.0058e18)
def cls(r, x):
    t = T.get(x[8])
    if t is None: return "unknown"
    if t["to"] == BOT: return "bot"
    if t["from"] == r["launch"]["from"]: return "launch"
    if t["from"] in crowd: return "crowd-eoa-other-route"
    return "other"
def replay_subset(P, a, b, keep):
    s, L = P.state_before(a)
    tokens = v4math.buy_out_int(s, L, Q, P.fee); s = sqrt_buy(s, L, Q, P.fee)
    for x in P.sw:
        if x[0] < a: continue
        if x[0] >= b: break
        if not keep(x): continue
        s = sqrt_buy(s, L, x[4], P.fee) if x[3] else sqrt_sell(s, L, x[5], P.fee)
    eth = v4math.sell_out_int(s, L, tokens, P.fee)
    return (eth - Q) / Q - GAS_ETH / 0.0058
flow = C.Counter(); nsw = C.Counter(); full = []; only_bot = []; only_oth = []; none_ = []; fps = C.Counter(); unk = 0
bot_sells = []; bot_sell_pools = 0; bot_buys_after = []; pools_with_other_buy = 0; other_buy_eth = []
for pid in samp:
    r = rows[pid]; P = Pool(r, E[pid]); tb = R["trig"][pid]; a = tb[0] + 2; b = a + 60
    rr = P.replay(a, b, Q)
    full.append(-1.0 if rr["pulled_le"] else rr["ret"])
    pulled = rr["pulled_le"]
    ob = replay_subset(P, a, b, lambda x: cls(r, x) == "bot"); oo = replay_subset(P, a, b, lambda x: cls(r, x) != "bot"); nn = replay_subset(P, a, b, lambda x: False)
    only_bot.append(-1.0 if pulled else ob); only_oth.append(-1.0 if pulled else oo); none_.append(-1.0 if pulled else nn)
    seen_other = False
    for x in P.sw:
        if a <= x[0] < b:
            c = cls(r, x); unk += c == "unknown"
            flow[(c, "B" if x[3] else "S")] += x[4]; nsw[(c, "B" if x[3] else "S")] += 1
            if c != "bot" and x[3]:
                t = T.get(x[8]); fps[(t["to"][:10], t["selector"], t["calldata_len"]) if t else None] += 1
                if x[4] >= 10**15: seen_other = True; other_buy_eth.append(x[4] / 1e18)
    pools_with_other_buy += seen_other
    end = P.first_pull if P.first_pull else P.lb + 3000
    sl = [x for x in P.sw if tb[0] <= x[0] <= min(end, tb[0] + 400) and not x[3] and cls(r, x) == "bot"]
    if sl: bot_sell_pools += 1
    for x in sl: bot_sells.append((x[0] - tb[0], x[4] / 1e18, (P.first_pull - x[0]) if P.first_pull else None))
    bb = [x for x in P.sw if tb[0] <= x[0] < tb[0] + 162 and x[3] and cls(r, x) == "bot"]
    bot_buys_after.append(len(bb))
n = len(samp)
def s(xs): return f"mean {sum(xs)/len(xs):+.4f} med {pct(xs,0.5):+.4f} win {sum(1 for v in xs if v > 0)/len(xs):.0%}"
print(f"sample {n} pools; unattributed swaps in [a,b): {unk}")
print("trade trig+2 / hold 60, all swaps:        ", s(full))
print("  only the bot's swaps re-applied:          ", s(only_bot))
print("  only the non-bot swaps re-applied:        ", s(only_oth))
print("  no swap re-applied (our two fees only):   ", s(none_))
print("flows in [a, b) by class (ETH; buys in / sells out):")
for k in sorted(nsw): print(f"  {k[0]:22s} {k[1]} n {nsw[k]:5d} eth {flow[k]/1e18:9.3f}")
print("non-bot buys in [a,b): fingerprints", fps.most_common(8))
print(f"pools with a non-bot buy >= 0.001 ETH in [a,b): {pools_with_other_buy}/{n}; sizes p10/50/90 {p3(other_buy_eth)}")
print(f"bot buys in [T, T+162) per pool p10/50/90 {p3(bot_buys_after)}")
print(f"bot sells in [T, min(pull, T+400)]: {len(bot_sells)} in {bot_sell_pools}/{n} pools; offset after its first buy p10/50/90 {p3([x[0] for x in bot_sells])}; "
      f"min {min((x[0] for x in bot_sells), default=None)}; ETH out p10/50/90 {p3([x[1] for x in bot_sells])}; blocks before the pull p10/50/90 {p3([x[2] for x in bot_sells if x[2] is not None])}")
within62 = sum(1 for x in bot_sells if x[0] < 62); print(f"bot sells inside a trig+2..+62 hold: {sum(1 for x in bot_sells if 2 <= x[0] < 62)}; first bot sell per pool offset:",
      sorted(min(x[0] for x in bot_sells if True) for _ in [0]) if bot_sells else None)
json.dump({"bot_sells": bot_sells, "full": full, "only_bot": only_bot, "only_oth": only_oth, "none": none_}, open(os.path.join(V, "v08_attrib.json"), "w"))
