#!/usr/bin/env python3
"""Feed-level look at PM1444 v3.0 launches from full blocks (vbot/blocks, as the sequencer feed carries them) joined with the pool's
Swap/ModifyLiquidity logs (others/cache_plogs.pkl): the launch tx in its block, every tx carrying the token, the engine's buy matching
(on_buy: value > 0, calldata >= 20 bytes, the token's 20 bytes in calldata, to != token) against the real swaps, the bot's router buys
and Universal Router sells decoded from calldata, and the timing of the first buys and sells.

    python3 sample_feed.py [SPAN]        (writes vbot/sample_feed.json)
"""
import sys, os, json, pickle, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
import fetch_blocks as fb
from vbot_feed import launch_of, bot_buy, ur_swaps, BOT_ROUTER, UNIVERSAL_ROUTER, POSITION_MANAGER
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
SYS_TYPES = {"0x64", "0x65", "0x66", "0x68", "0x69", "0x6a"}          # Arbitrum system / deposit types: not user transactions
MINW = 2 * 10**14
SPAN = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def s256(x): return x - (1 << 256) if x >> 255 else x
def s128(x):
    x = s256(x); return x - (1 << 128) if x >= (1 << 127) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)


R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
V3 = {r["b0"]: r for r in R if fam(r)}
PL = pickle.load(open(os.path.join(SCR, "others", "cache_plogs.pkl"), "rb"))


def analyse(b0, B):
    r = V3[b0]; pid = r["pid"]; tok = r["token"][2:].lower(); tb = bytes.fromhex(tok)
    if any(n not in B for n in range(b0, b0 + SPAN + 1)):
        return None
    # swaps / liquidity by tx
    sw = collections.defaultdict(list); pull = None
    for bn, li, t0, snd, d, th in sorted(PL.get(pid, []), key=lambda x: (x[0], x[1])):
        if bn > b0 + SPAN + 50: break
        if t0 == T_SWAP: sw[th].append((bn, li, s128(W(d, 0)), s128(W(d, 1)), snd[-40:]))
        elif s256(W(d, 2)) < 0 and pull is None: pull = bn
    ts0, bf0, txs0 = B[b0]
    user0 = [t for t in txs0 if t[6] not in SYS_TYPES]
    L = [t for t in txs0 if t[1] == r["tx"]]
    lt = L[0] if L else None
    dec = launch_of(lt[3][2:], lt[4], lt[9]) if lt else None
    out = {"b0": b0, "pid": pid, "token": tok, "pull": (pull - b0) if pull else None, "launch_found": lt is not None, "launch_decoded_pid_ok": bool(dec and dec["pid"] == pid),
           "launch_idx": lt[0] if lt else None, "block_user_txs": len(user0), "block_all_txs": len(txs0),
           "same_block_others": [(t[2][:10], t[3][:10], len(t[9]), t[4] / 1e18, t[9][:4].hex()) for t in user0 if t[1] != r["tx"]],
           "other_family_launches_same_block": sum(1 for t in user0 if t[1] != r["tx"] and launch_of(t[3][2:], t[4], t[9]) is not None),
           "deployer": lt[2] if lt else None, "deployer_nonce": lt[5] if lt else None}
    rows = []
    for n in range(b0, b0 + SPAN + 1):
        ts, bf, txs = B[n]
        for t in txs:
            idx, h, frm, to, val, nonce, typ, gas, tip, data = t
            if h == r["tx"]: continue
            has_tok = tb in data
            s = sw.get(h, [])
            if not has_tok and not s: continue
            to_ = to[2:]
            matched = val > 0 and len(data) >= 20 and has_tok and to_ != tok
            bb = bot_buy(to_, val, data); us = [x for x in ur_swaps(to_, val, data) if x["pid"] == pid]
            a0 = sum(x[2] for x in s); a1 = sum(x[3] for x in s)
            rows.append({"off": n - b0, "idx": idx, "hash": h, "from": frm, "nonce": nonce, "to": to_, "sel": data[:4].hex(), "len": len(data), "value": val, "tip": tip, "gas": gas,
                         "type": typ, "bb_tok_ok": bool(bb and bb["token"] == tok and bb["fee"] == 10000 and bb["tick_spacing"] == 200), "matched": matched, "has_tok": has_tok, "swap": bool(s), "a0": a0, "a1": a1, "n_swaps": len(s),
                         "bot_buy": ({k: v for k, v in bb.items() if k in ("token", "w3", "w4", "recipient", "deadline", "fee", "tick_spacing", "hooks", "ur", "pm")} | {"deadline_minus_ts": bb["deadline"] - ts}) if bb else None,
                         "ur": [{"zf1": x["zero_for_one"], "amount_in": x["amount_in"], "min_out": x["min_out"]} for x in us], "ts": ts})
    out["rows"] = rows
    buys = [x for x in rows if x["swap"] and x["a0"] < 0]; sells = [x for x in rows if x["swap"] and x["a0"] > 0]
    real = [x for x in buys if -x["a0"] >= MINW]
    out["first_buy"] = real[0]["off"] if real else None; out["second_buy"] = real[1]["off"] if len(real) > 1 else None
    out["first_sell"] = next((x["off"] for x in sells if x["a0"] >= MINW), None)
    out["bot_router_buys"] = [x["off"] for x in buys if x["to"] == BOT_ROUTER]
    return out


if __name__ == "__main__":
    B = {}
    for c in sorted(int(f[:-4]) for f in os.listdir(fb.BD) if f.endswith(".pkl")):
        B.update(fb.load_chunk(c))
    res = [x for x in (analyse(b0, B) for b0 in sorted(V3) if b0 in B) if x]
    print("launches with full blocks [b0, b0 + %d]:" % SPAN, len(res))
    # 1. the launch in its block
    print("\nlaunch tx found in its block:", sum(x["launch_found"] for x in res), "| decoded from calldata with the right pool id:", sum(x["launch_decoded_pid_ok"] for x in res))
    print("user txs in the launch block:", collections.Counter(x["block_user_txs"] for x in res).most_common())
    print("launch index in block:", collections.Counter(x["launch_idx"] for x in res).most_common())
    print("other family launches in the same block:", collections.Counter(x["other_family_launches_same_block"] for x in res).most_common())
    oth = collections.Counter((o[1], o[4]) for x in res for o in x["same_block_others"]); print("other txs in launch blocks (to, sel):", oth.most_common(8))
    # 2. buys and the engine's matching
    allr = [y for x in res for y in x["rows"]]
    buys = [y for y in allr if y["swap"] and y["a0"] < 0]; sells = [y for y in allr if y["swap"] and y["a0"] > 0]
    print(f"\nswap txs on the pools in [b0, b0+{SPAN}]: buys {len(buys)}  sells {len(sells)}")
    for name, xs in (("buys", buys), ("buys >= 0.0002 ETH", [y for y in buys if -y["a0"] >= MINW])):
        print(f"  {name}: {len(xs)}; to: {collections.Counter(y['to'][:8] for y in xs).most_common(5)}; sel/len: {collections.Counter((y['sel'], y['len']) for y in xs).most_common(5)}")
        print(f"     engine-matched (value>0, token in calldata): {sum(y['matched'] for y in xs)}; tx.value == ETH into the pool: {sum(1 for y in xs if y['value'] == -y['a0'])}; token in calldata: {sum(y['has_tok'] for y in xs)}")
    bot = [y for y in buys if y["to"] == BOT_ROUTER]
    print(f"  bot-router buys: {len(bot)}; decoded by bot_buy: {sum(1 for y in bot if y['bot_buy'])}; token/fee/ts words == the pool's: {sum(1 for y in bot if y['bb_tok_ok'])}")
    bb = [y for y in bot if y["bot_buy"]]
    for k in ("ur", "pm", "fee", "tick_spacing", "hooks", "w3", "deadline_minus_ts"):
        print(f"     {k}: {collections.Counter(y['bot_buy'][k] for y in bb).most_common(4)}")
    print("     w4 / tokens out (min-out ratio): p10/50/90", [round(sorted(y['bot_buy']['w4'] / y['a1'] for y in bb if y['a1'] > 0)[int(q * (len(bb) - 1))], 4) for q in (.1, .5, .9)])
    print("     buy size ETH p10/50/90:", [round(sorted(-y['a0'] / 1e18 for y in bb)[int(q * (len(bb) - 1))], 4) for q in (.1, .5, .9)], " tip:", collections.Counter(y["tip"] for y in bb).most_common(4))
    print("     buyer nonce range:", min(y["nonce"] for y in bb), max(y["nonce"] for y in bb), " distinct wallets:", len({y["from"] for y in bb}), " gas:", collections.Counter(y["gas"] for y in bb).most_common(3))
    fm = [y for y in allr if y["matched"] and not (y["swap"] and y["a0"] < 0)]
    print(f"  engine-matched txs that are NOT a buy on this pool: {len(fm)}: {collections.Counter((y['to'][:8], y['sel'], y['len'], y['swap']) for y in fm).most_common(6)}")
    nm = [y for y in buys if not y["matched"]]
    print(f"  buys the engine's matching misses: {len(nm)}: {collections.Counter((y['to'][:8], y['sel'], y['len'], y['value'] > 0, y['has_tok']) for y in nm).most_common(6)};"
          f" ETH {sum(-y['a0'] for y in nm) / 1e18:.4f} of {sum(-y['a0'] for y in buys) / 1e18:.4f}")
    # 3. sells
    print(f"\n  sells: {len(sells)}; to: {collections.Counter(y['to'][:8] for y in sells).most_common(4)}; sel/len: {collections.Counter((y['sel'], y['len']) for y in sells).most_common(4)}; value>0: {sum(1 for y in sells if y['value'] > 0)}")
    us = [y for y in sells if y["ur"]]
    print(f"     decoded by ur_swaps (zeroForOne False): {sum(1 for y in us if not y['ur'][0]['zf1'])}; amount_in == tokens into the pool: {sum(1 for y in us if sum(z['amount_in'] for z in y['ur']) == -y['a1'])}")
    sw_bot = {y["from"] for y in bot}
    print(f"     sellers that are bot-router buyers (in this sample): {sum(1 for y in sells if y['from'] in sw_bot)} of {len(sells)}")
    print("     sell min_out (wei):", collections.Counter(z["min_out"] for y in us for z in y["ur"]).most_common(3))
    # reverted / no-swap txs carrying the token with value
    nos = [y for y in allr if y["has_tok"] and not y["swap"]]
    print(f"\n  txs carrying the token with no swap on the pool (reverted, or other): {len(nos)}: {collections.Counter((y['to'][:8], y['sel'], y['len'], y['value'] > 0) for y in nos).most_common(8)}")
    # 4. timing
    def q(v):
        v = sorted(v); return [v[int(p * (len(v) - 1))] for p in (0, .1, .5, .9, 1)] if v else None
    print("\nfirst buy >= 0.0002 offset (min/p10/med/p90/max):", q([x["first_buy"] for x in res if x["first_buy"] is not None]), collections.Counter(x["first_buy"] for x in res).most_common(6))
    print("second buy offset:", q([x["second_buy"] for x in res if x["second_buy"] is not None]))
    print("first sell offset:", q([x["first_sell"] for x in res if x["first_sell"] is not None]))
    print("bot router buys: first", q([x["bot_router_buys"][0] for x in res if x["bot_router_buys"]]), " second", q([x["bot_router_buys"][1] for x in res if len(x["bot_router_buys"]) > 1]))
    print("first real buy by the bot router:", sum(1 for x in res if x["first_buy"] is not None and x["bot_router_buys"] and x["bot_router_buys"][0] == x["first_buy"]), "of", len(res))
    print("pull offset:", q([x["pull"] for x in res if x["pull"] is not None]), "not pulled in window:", sum(1 for x in res if x["pull"] is None))
    json.dump(res, open(os.path.join(HERE, "sample_feed.json"), "w"), default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
