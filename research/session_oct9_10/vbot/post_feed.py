#!/usr/bin/env python3
"""Out-of-sample feed check on 16 launches after the census (Oct 9 14:48 - 21:xx UTC): full blocks [b0 - 3, b0 + 100] (vbot/blocks) and
the pool logs from others/verify/cache_post.pkl ([b0, b0 + 400]). Same checks as replay_window: strict fingerprint on the launch tx,
buys by the engine's rule, sells by the UR decoder, the pull by the bot-router decoder, exact price copy, timing.  python3 post_feed.py"""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
import fetch_blocks as fb
from vbot_feed import launch_of, bot_buy, ur_swaps, bot_pull, permit2_approve, nft_approve, buy_sqrt, sell_sqrt, BOT_ROUTER
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
SYS_TYPES = {"0x64", "0x65", "0x66", "0x68", "0x69", "0x6a"}; MINW = 2 * 10**14
def s256(x): return x - (1 << 256) if x >> 255 else x
def s128(x):
    x = s256(x); return x - (1 << 128) if x >= (1 << 127) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
PC = pickle.load(open(os.path.join(HERE, "cache_post_launch.pkl"), "rb"))
PP = pickle.load(open(os.path.join(SCR, "others", "verify", "cache_post.pkl"), "rb"))["plogs"]
rng = [tuple(map(int, x.split("-"))) for x in open(os.path.join(HERE, "post_ranges.txt")).read().split()]
INIT = {int(l["blockNumber"], 16): l for l in PC["inits"]}
tot = collections.Counter(); timing = []
for a, z in rng:
    b0 = a + 3; B = fb.get(a, z)
    inits = [l for l in PC["inits"] if int(l["blockNumber"], 16) == b0]
    p = None
    for t in B[b0][2]:
        q = launch_of(t[3][2:], t[4], t[9])
        if q and any(l["topics"][1] == q["pid"] and l["transactionHash"] == t[1] for l in inits): p = q; p["idx"] = t[0]; p["n_user"] = sum(1 for x in B[b0][2] if x[6] not in SYS_TYPES)
    if p is None:
        tot["launch not recognised"] += 1; continue
    tot["launches recognised (strict, pid == Initialize)"] += 1
    pid = p["pid"]; tb = p["token_bytes"]; sp = p["sqrt_p"]; L = p["liq"]; fee = p["fee"]
    logs_ = sorted(PP.get(pid, []), key=lambda x: (x[0], x[1]))
    real = {}
    for bn, li, t0, snd, d, th in logs_:
        if bn > z: continue
        if t0 == T_SWAP: real.setdefault(th, []).append((bn, s128(W(d, 0)), s128(W(d, 1)), W(d, 2)))
        elif s256(W(d, 2)) < 0: real.setdefault(th, []).append((bn, "pull"))
    seen = {}; buys_off = []; pulled = False; err = []; fb_rows = []
    for n in range(b0, z + 1):
        for t in B[n][2]:
            idx, h, frm, to, val, nonce, typ, gas, tip, data = t
            if typ in SYS_TYPES or tb not in data or (n == b0 and idx <= p["idx"]): continue
            to_ = to[2:]
            if val > 0 and len(data) >= 20 and to_ != p["token"]:
                seen[h] = "B"; sp = buy_sqrt(sp, L, val, fee) if not pulled else sp
                if val >= MINW: buys_off.append((n - b0, to_ == BOT_ROUTER, bool(bot_buy(to_, val, data))))
            elif [x for x in ur_swaps(to_, val, data) if x["pid"] == pid]:
                seen[h] = "S"
                for x in ur_swaps(to_, val, data):
                    if x["pid"] == pid and not pulled: sp = sell_sqrt(sp, L, x["amount_in"], fee) if not x["zero_for_one"] else buy_sqrt(sp, L, x["amount_in"], fee)
            elif bot_pull(to_, val, data): seen[h] = "P"; pulled = True
            elif permit2_approve(to_, val, data): seen[h] = "A"
            else: seen[h] = "?"
            r = real.get(h)
            if r and r[-1][1] != "pull" and not pulled:
                err.append(abs(sp - r[-1][3]) / r[-1][3])
    for th, r in real.items():
        kind = "P" if r[-1][1] == "pull" else ("B" if r[-1][1] < 0 else ("S" if r[-1][1] > 0 else "0"))
        tot[f"real {kind}"] += 1; tot[f"real {kind} seen as {seen.get(th, 'not seen')}"] += 1
    tot["price copy exact after swaps"] += sum(1 for e in err if e == 0); tot["price copy inexact"] += sum(1 for e in err if e != 0)
    tot["feed '?' (token in calldata, unexplained)"] += sum(1 for v in seen.values() if v == "?")
    timing.append({"b0": b0, "idx": p["idx"], "n_user": p["n_user"], "first": buys_off[0] if buys_off else None, "second": buys_off[1] if len(buys_off) > 1 else None})
for k in sorted(tot): print(f"  {k}: {tot[k]}")
print("launch idx / user txs in block:", [(x["idx"], x["n_user"]) for x in timing])
print("first real buy (offset, to bot router, decoded):", [x["first"] for x in timing])
print("second real buy:", [x["second"] for x in timing])
json.dump({"tot": tot, "timing": timing}, open(os.path.join(HERE, "post_feed.json"), "w"))
