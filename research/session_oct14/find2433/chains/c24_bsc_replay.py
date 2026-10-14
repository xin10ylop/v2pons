"""Replay of the front trade on the BNB 12.4333285 line: our buy of X BNB at the start of block +1, then every recorded swap re-priced in
order with exact v4 integer math (buys keep their BNB in, sells keep their tokens in; a bot buy whose output falls under its calldata minOut is
dropped as a revert), and our sale either (a) right after the bot's first buy (same block, needs ordering) or (b) at the start of the next block.
Also the margin to the operator's pull reaction (6-7 blocks after an outsider buy)."""
import sys, json, collections; sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/v2pons/src')
import v4math
RC = "0x07cb61618b69234d954022ff738a015548715533"; FEE = 5000
L = {r["id"]: r for r in json.load(open("c18_launches.json"))}
TX = {}
for l in open("c18_swaptx_cache.jsonl"):
    r = json.loads(l); TX[r["h"]] = r
E = [json.loads(l) for l in open("c18_events_cache.jsonl")]
def s256(x): return x - (1 << 256) if x >= (1 << 255) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
by = collections.defaultdict(list)
for e in E: by[e["id"]].append(e)
def buy(sp, L_, x):
    out = v4math.buy_out_int(sp, L_, x, FEE); xf = x - (x * FEE + 999_999) // 1_000_000
    return out, int(v4math.sqrt_after_buy(sp, L_, xf))
def sell(sp, L_, t):
    out = v4math.sell_out_int(sp, L_, t, FEE); tf = t - (t * FEE + 999_999) // 1_000_000
    return out, sp + (tf * (1 << 96)) // L_
res = []
for pid, r in L.items():
    if abs(r["value"] / 1e18 - 12.4333285) > 1e-6: continue
    ev = sorted([e for e in by[pid] if e["k"] == "swap"], key=lambda e: (e["b"], e["li"]))
    b0 = r["b"]; liq = r["liq"][0]
    pull = min([e["b"] - b0 for e in by[pid] if e["k"] == "liq" and s256(W(e["d"], 2)) < 0])
    fb = next(i for i, e in enumerate(ev) if TX.get(e["tx"], {}).get("to") == RC and TX[e["tx"]]["sel"] == "0xc1120e3d")
    fb_off = ev[fb]["b"] - b0
    for X in [0.01, 0.02, 0.032, 0.05]:
        Xw = int(X * 1e18); sp = r["sqrtP"]
        tok, sp = buy(sp, liq, Xw)                  # our buy, start of block +1 (no swap happens before the bot's first buy in any pool)
        reverts = 0; outa = outb = None
        for i, e in enumerate(ev):
            if e["b"] - b0 > fb_off and outb is None:   # (b) start of the block after the bot's first buy
                outb, _ = sell(sp, liq, tok)
            if e["b"] - b0 > fb_off + 1: break
            t = TX.get(e["tx"], {}); a0, a1 = s256(W(e["d"], 0)), s256(W(e["d"], 1))
            if a0 < 0:   # a buy: BNB in
                o, sp2 = buy(sp, liq, -a0)
                if t.get("to") == RC and t.get("sel") == "0xc1120e3d":
                    mo = int(t["inp"][10 + 64 * 4: 10 + 64 * 5], 16)
                    if o < mo: reverts += 1; continue
                sp = sp2
            elif a1 < 0:  # a sell: tokens in
                _, sp = sell(sp, liq, -a1)
            if i == fb: outa, _ = sell(sp, liq, tok)   # (a) right after the bot's first buy
        if outb is None: outb, _ = sell(sp, liq, tok)
        res.append({"b0": b0, "X": X, "fb_off": fb_off, "pull": pull, "bot_first_reverted": reverts > 0 and outa is None,
                    "ret_a": (outa / Xw - 1) if outa else None, "ret_b": outb / Xw - 1, "reverts": reverts})
json.dump(res, open("c24_bsc_replay.json", "w"), indent=1)
pc = lambda v, q: sorted(v)[min(len(v) - 1, int(q * len(v)))] if v else None
for X in [0.01, 0.02, 0.032, 0.05]:
    g = [x for x in res if x["X"] == X]; a = [x["ret_a"] for x in g if x["ret_a"] is not None]; b = [x["ret_b"] for x in g]
    print(f"X={X} BNB pools={len(g)} bot-buy reverts={sum(x['reverts'] for x in g)} | sell right after bot's 1st buy: p10/p50/p90 {pc(a,.1):+.3%}/{pc(a,.5):+.3%}/{pc(a,.9):+.3%} positive {sum(1 for v in a if v>0)}/{len(a)} mean {sum(a)/len(a):+.3%}"
          f" | sell next block: p10/p50/p90 {pc(b,.1):+.3%}/{pc(b,.5):+.3%}/{pc(b,.9):+.3%} positive {sum(1 for v in b if v>0)}/{len(b)} mean {sum(b)/len(b):+.3%}")
g = [x for x in res if x["X"] == 0.032]
print("exit block (fb_off+1) vs reaction pull if our +1 buy triggers it (+7..+8):", collections.Counter(x["fb_off"] + 1 for x in g))
