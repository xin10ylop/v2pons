#!/usr/bin/env python3
"""Replay a contiguous window of full blocks (vbot/blocks) the way the engine reads the feed, with the recognition this family needs:

  * every transaction is tested against the launch fingerprint at several levels; strict matches are armed at once from calldata
    (no receipt) and checked against the census (pool id, Initialize) -> the feed-level false-positive count;
  * on armed pools: buys by the engine's own rule (value > 0, calldata >= 20 bytes, token bytes in calldata, to != token), sells by the
    Universal Router decoder (V4_SWAP / SWAP_EXACT_IN_SINGLE, zeroForOne false, exact amountIn), Permit2 approvals of the token;
  * the engine's copy of the pool price is moved by every detected buy (and, in a second copy, every detected sell) with the PoolManager's
    integer arithmetic, and compared after every real swap with the Swap log's sqrtPriceX96 -> how exact the copy is with and without sells;
  * every real swap on the armed pools (from the census log cache) is checked to have been seen in the feed replay, and vice versa.

    python3 replay_window.py A B        (writes vbot/replay_<A>_<B>.json)
"""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE)
import fetch_blocks as fb
from launch_decode import decode_1444
from vbot_feed import launch_of, bot_buy, ur_swaps, bot_pull, permit2_approve, nft_approve, sell_sqrt, buy_sqrt, POSITION_MANAGER, BOT_ROUTER, UNIVERSAL_ROUTER
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
PERMIT2 = "000000000022d473030f116ddee9f6b43ac78ba3"
SYS_TYPES = {"0x64", "0x65", "0x66", "0x68", "0x69", "0x6a"}
Q96 = 1 << 96; MINW = 2 * 10**14
def s256(x): return x - (1 << 256) if x >> 255 else x
def s128(x):
    x = s256(x); return x - (1 << 128) if x >= (1 << 127) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)


def net(x, fee): return x * (1_000_000 - fee) // 1_000_000                          # SwapMath: amountRemainingLessFee (floor)
def buy_int(sp, L, x, fee):                                                          # getNextSqrtPriceFromAmount0RoundingUp
    n1 = L << 96; xn = net(x, fee); return -(-(n1 * sp) // (n1 + xn * sp))
def sell_int(sp, L, x, fee):                                                         # getNextSqrtPriceFromAmount1RoundingDown
    return sp + (net(x, fee) << 96) // L


A, Bz = int(sys.argv[1]), int(sys.argv[2])
R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
fam = lambda r: (r["to"] or "").lower() == "0x" + POSITION_MANAGER and r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
BYPID = {r["pid"]: r for r in R}
CENSUS_TX = {r["tx"]: r for r in R}
PL = pickle.load(open(os.path.join(SCR, "others", "cache_plogs.pkl"), "rb"))
BL = fb.get(A, Bz)
missing = [n for n in range(A, Bz + 1) if n not in BL]
print(f"window {A}-{Bz}: {Bz - A + 1} blocks, {len(missing)} missing", flush=True)
if missing: raise SystemExit("fetch the window first")

lv = collections.Counter(); lv_nonfam = collections.defaultdict(list)
to_pm = collections.Counter()
armed = {}; ev = []; n_user = 0; deployers = {}
for n in range(A, Bz + 1):
    ts, bf, txs = BL[n]
    for t in txs:
        idx, h, frm, to, val, nonce, typ, gas, tip, data = t
        if typ in SYS_TYPES: continue
        n_user += 1; to_ = to[2:]
        if frm[2:] in deployers:
            dp = deployers[frm[2:]]; dp["txs"].append((n - dp["launch_seq"], idx, nonce, to_[:10], data[:4].hex(), len(data), val, data[4:].hex() if len(data) <= 100 else None))
        if to_ == POSITION_MANAGER:
            to_pm[(data[:4].hex(), len(data), "value>0" if val else "value0")] += 1
            l1 = data[:4].hex() == "ac9650d8"; l2 = l1 and len(data) == 1444; d = decode_1444(data) if l2 else None
            l4 = launch_of(to_, 3 * 10**18, data, strict=False) is not None; l5 = launch_of(to_, val, data, strict=False) is not None
            p = launch_of(to_, val, data, strict=True)
            r = CENSUS_TX.get(h); isfam = bool(r and fam(r))
            for name, ok in (("L1 PM+ac9650d8", l1), ("L2 +1444 bytes", l2), ("L3 +layout", d is not None), ("L4 +key fee1% ts200 nohook fullrange", l4), ("L5 +value 3 ETH", l5), ("L6 strict", p is not None)):
                if ok:
                    lv[name] += 1
                    if not isfam: lv_nonfam[name].append((n, h[:12], data[:4].hex(), len(data), val / 1e18, (r or {}).get("fee"), (r or {}).get("ts"), "census pool" if r else "no pool in census"))
            if p is not None:
                p.update({"launch_seq": n, "launch_idx": idx, "tx": h, "census": isfam, "pid_ok": bool(r and r["pid"] == p["pid"]), "sp_b": p["sqrt_p"], "sp_bs": p["sqrt_p"],
                          "buys": [], "sells": [], "approvals": [], "fp": []})
                armed[p["pid"]] = p; p["txs"] = []; deployers[frm[2:]] = p
            continue
        for pid, p in armed.items():
            if p["token_bytes"] not in data: continue
            if val > 0 and len(data) >= 20 and to_ != p["token"]:
                p["buys"].append((n, idx, h, val, frm, to_)); p["sp_b"] = buy_int(p["sp_b"], p["liq"], val, p["fee"]); p["sp_bs"] = buy_int(p["sp_bs"], p["liq"], val, p["fee"])
                ev.append((pid, n, idx, h, "B", p["sp_b"], p["sp_bs"]))
            else:
                us = [x for x in ur_swaps(to_, val, data) if x["pid"] == pid]
                if us:
                    for x in us:
                        if x["zero_for_one"]: p["sp_bs"] = buy_int(p["sp_bs"], p["liq"], x["amount_in"], p["fee"])
                        else: p["sp_bs"] = sell_int(p["sp_bs"], p["liq"], x["amount_in"], p["fee"])
                    p["sells"].append((n, idx, h, sum(x["amount_in"] for x in us if not x["zero_for_one"]), frm, to_))
                    ev.append((pid, n, idx, h, "S", p["sp_b"], p["sp_bs"]))
                elif permit2_approve(to_, val, data):
                    a = permit2_approve(to_, val, data); p["approvals"].append((n, idx, h, frm, a["spender"] == UNIVERSAL_ROUTER))
                elif bot_pull(to_, val, data):
                    p["pull_feed"] = p.get("pull_feed") or (n, idx, h, frm == "0x" + p["owner"], bot_pull(to_, val, data)["token"] == p["token"])
                else:
                    p["fp"].append((n, idx, h, to_[:10], data[:4].hex(), len(data), val))
            break

print(f"user txs {n_user}; txs to the PositionManager {sum(to_pm.values())}: {to_pm.most_common(8)}")
print("fingerprint levels (txs in the feed window) -> matches, of which not a census family launch:")
for name in ("L1 PM+ac9650d8", "L2 +1444 bytes", "L3 +layout", "L4 +key fee1% ts200 nohook fullrange", "L5 +value 3 ETH", "L6 strict"):
    nf = lv_nonfam[name]
    print(f"   {name:38s} {lv[name]:5d}  non-family {len(nf):4d}  {collections.Counter((x[2], x[3], round(x[4], 3), x[5], x[6], x[7]) for x in nf).most_common(4)}")
fam_in_window = [r for r in R if fam(r) and A <= r["b0"] <= Bz]
print(f"census family launches in the window: {len(fam_in_window)}; armed by the strict fingerprint: {len(armed)}; pid == census pid: {sum(p['pid_ok'] for p in armed.values())}; "
      f"missed: {len({r['pid'] for r in fam_in_window} - set(armed))}")

# compare with the real swaps
tot = collections.Counter(); err_b = []; err_bs = []; err2_b = []; err2_bs = []; late = collections.Counter(); per = []
for pid, p in armed.items():
    b0 = p["launch_seq"]
    real = [(bn, li, s128(W(d, 0)), s128(W(d, 1)), W(d, 2), th) for bn, li, t0, snd, d, th in sorted(PL.get(pid, []), key=lambda x: (x[0], x[1])) if t0 == T_SWAP and bn <= Bz]
    pulls = [bn for bn, li, t0, snd, d, th in PL.get(pid, []) if t0 == T_ML and s256(W(d, 2)) < 0 and bn <= Bz]
    end = min(Bz, b0 + 3000)                                                       # the census log cache covers [b0, b0 + 3000]
    real = [x for x in real if x[0] <= end]
    rb = {x[5] for x in real if x[2] < 0}; rs = {x[5] for x in real if x[2] > 0}
    fb_ = {x[2] for x in p["buys"] if x[0] <= end}; fs = {x[2] for x in p["sells"] if x[0] <= end}
    p["nos"] = sorted((fb_ | fs) - rb - rs)
    tot["real buys"] += len(rb); tot["real sells"] += len(rs); tot["feed buys"] += len(fb_); tot["feed sells"] += len(fs)
    tot["real buys seen as buys"] += len(rb & fb_); tot["real sells seen as sells"] += len(rs & fs)
    tot["feed buys with no swap"] += len(fb_ - rb - rs); tot["feed sells with no swap"] += len(fs - rs - rb)
    tot["real buys not seen"] += len(rb - fb_); tot["real sells not seen"] += len(rs - fs)
    tot["other txs carrying the token"] += len(p["fp"]); tot["permit2 approvals"] += len(p["approvals"])
    pf = p.get("pull_feed"); pf = pf if pf and pf[0] <= end else None
    if pulls or pf:
        tot["pulls (logs)"] += bool(pulls); tot["pulls seen in feed (bot router a0f7978d)"] += bool(pf)
        tot["pull feed block == log block"] += bool(pulls and pf and pf[0] == min(pulls)); tot["pull sent by the deployer"] += bool(pf and pf[3])
    # price copy vs the pool, after each real swap tx (last swap of that tx)
    evd = {e[3]: e for e in ev if e[0] == pid}
    last = {}
    for x in real: last[x[5]] = x
    for th, x in last.items():
        e = evd.get(th)
        if e is None: continue
        if pulls and x[0] >= min(pulls): continue                                   # liquidity changed: the single-L copy no longer applies
        err_b.append(abs(e[5] - x[4]) / x[4]); err_bs.append(abs(e[6] - x[4]) / x[4])
    rbuys = [x for x in real if x[2] <= -MINW]
    if len(rbuys) > 1 and rbuys[1][5] in evd and not (pulls and rbuys[1][0] >= min(pulls)):
        e = evd[rbuys[1][5]]; x = last[rbuys[1][5]]
        err2_b.append(abs(e[5] - x[4]) / x[4]); err2_bs.append(abs(e[6] - x[4]) / x[4])
    per.append({"pid": pid, "b0": b0, "idx": p["launch_idx"], "n_buys": len(rb), "n_sells": len(rs), "first_buy": (rbuys[0][0] - b0) if rbuys else None,
                "second_buy": (rbuys[1][0] - b0) if len(rbuys) > 1 else None, "pull": (min(pulls) - b0) if pulls else None,
                "fp": p["fp"][:5], "approvals": len(p["approvals"]), "no_swap": p["nos"], "deployer_txs": p["txs"], "pull_feed": p.get("pull_feed"), "approvals_to_ur": sum(1 for a in p["approvals"] if a[4])})
print("\nswaps on the armed pools (to the window's end):", dict(tot))
def q(v):
    v = sorted(v); return [f"{v[int(p * (len(v) - 1))]:.1e}" for p in (0, .5, .9, .99, 1)] if v else None
print(f"price copy vs Swap log sqrtPriceX96 after each swap tx (before any pull): n {len(err_b)}")
print(f"   buys only (the engine today)   rel err min/med/p90/p99/max {q(err_b)}")
print(f"   buys and sells (UR decoder)     rel err min/med/p90/p99/max {q(err_bs)}  exact: {sum(1 for e in err_bs if e == 0)}")
print(f"   at the 2nd real buy (the take-profit moment), n {len(err2_b)}: buys only: exact {sum(1 for e in err2_b if e == 0)}, > 0.1% off {sum(1 for e in err2_b if e > 1e-3)} (max {max(err2_b) if err2_b else 0:.1e}); "
      f"buys and sells: exact {sum(1 for e in err2_bs if e == 0)}")
fp = [(x, pr["pid"][:10]) for pr in per for x in pr["fp"]]
print("other txs carrying an armed token (not a buy/sell/approval):", collections.Counter((x[0][3], x[0][4], x[0][5], x[0][6] > 0) for x in fp).most_common(8))
json.dump({"window": [A, Bz], "levels": dict(lv), "nonfam": {k: v[:50] for k, v in lv_nonfam.items()}, "to_pm": [[list(k), v] for k, v in to_pm.most_common(40)],
           "totals": dict(tot), "err_buys_only": sorted(err_b), "err_buys_sells": sorted(err_bs), "per": per}, open(os.path.join(HERE, f"replay_{A}_{Bz}.json"), "w"), default=str)
