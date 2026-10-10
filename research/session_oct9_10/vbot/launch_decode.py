#!/usr/bin/env python3
"""Decode a v4 PositionManager launch (multicall 0xac9650d8 = initializePool + modifyLiquidities) from its calldata alone, as the
engine sees it in the sequencer feed: the PoolKey, sqrtPriceX96, the pool id (keccak of the abi-encoded key), the MINT_POSITION
range and liquidity, and the active liquidity at the initial price. No receipt needed.

Two decoders:
  decode_launch(data)   generic ABI walk of multicall(bytes[]) -> initializePool(PoolKey,uint160) + modifyLiquidities(bytes,uint256)
                        (unlockData = abi.encode(bytes actions, bytes[] params); action 0x02 MINT_POSITION params =
                        abi.encode(PoolKey, int24 lo, int24 hi, uint256 liquidity, uint128 a0Max, uint128 a1Max, address owner, bytes hookData))
  decode_1444(data)     the fixed-offset fast path for the 1,444-byte layout (offsets in OFF below; every structural word checked)

    python3 launch_decode.py      tests both on every census PositionManager launch against its Initialize and ModifyLiquidity logs
"""
from eth_utils import keccak

SEL_MULTICALL = bytes.fromhex("ac9650d8"); SEL_INIT = bytes.fromhex("f7020405"); SEL_MODLIQ = bytes.fromhex("dd46508f")
A_MINT = 0x02; A_SETTLE_PAIR = 0x0d; A_SWEEP = 0x14; A_CLOSE = 0x12; A_SETTLE = 0x0b; A_TAKE_PAIR = 0x11; A_MINT_FROM_DELTAS = 0x05
Q96 = 1 << 96


def _u(b, o):
    return int.from_bytes(b[o:o + 32], "big")


def _s(b, o):
    x = _u(b, o); return x - (1 << 256) if x >> 255 else x


def _key(b, o):
    """PoolKey: 5 words at o"""
    return {"currency0": b[o + 12:o + 32].hex(), "currency1": b[o + 44:o + 64].hex(), "fee": _u(b, o + 64), "tick_spacing": _s(b, o + 96),
            "hooks": b[o + 140:o + 160].hex()}


def pool_id(b, o):
    """keccak256(abi.encode(PoolKey)) = keccak of the 5 words exactly as they sit in the calldata"""
    return "0x" + keccak(bytes(b[o:o + 160])).hex()


def _dyn_bytes(b, base, off_word_pos):
    """read an abi dynamic `bytes` whose offset (relative to `base`) is in the word at off_word_pos; returns (start, length)"""
    off = _u(b, off_word_pos); st = base + off; ln = _u(b, st)
    if st + 32 + ln > len(b):
        raise ValueError("bytes out of range")
    return st + 32, ln


def decode_launch(data):
    """generic decoder; None if the call is not a multicall holding initializePool (PoolKey + sqrtPriceX96)"""
    b = bytes(data)
    if len(b) < 4 + 64 or b[:4] != SEL_MULTICALL:
        return None
    try:
        base = 4; arr = base + _u(b, base); n = _u(b, arr)
        if n > 16:
            return None
        calls = []
        for i in range(n):
            st, ln = _dyn_bytes(b, arr + 32, arr + 32 + 32 * i); calls.append((st, ln))
        out = {"n_calls": n, "selectors": [b[st:st + 4].hex() for st, ln in calls]}
        for st, ln in calls:
            sel = b[st:st + 4]
            if sel == SEL_INIT and ln >= 4 + 192 and "key" not in out:
                k = st + 4
                out["key"] = _key(b, k); out["pid"] = pool_id(b, k); out["sqrt_p"] = _u(b, k + 160); out["key_off"] = k; out["sqrt_off"] = k + 160
            elif sel == SEL_MODLIQ and "mints" not in out:
                a = st + 4                                                     # modifyLiquidities(bytes unlockData, uint256 deadline)
                ust, uln = _dyn_bytes(b, a, a); out["deadline"] = _u(b, a + 32)
                ast, aln = _dyn_bytes(b, ust, ust)                             # unlockData = abi.encode(bytes actions, bytes[] params)
                actions = b[ast:ast + aln]; out["actions"] = actions.hex()
                parr = ust + _u(b, ust + 32); pn = _u(b, parr)
                mints = []
                for j in range(min(pn, len(actions))):
                    pst, pln = _dyn_bytes(b, parr + 32, parr + 32 + 32 * j)
                    if actions[j] == A_MINT and pln >= 32 * 12:
                        mk = _key(b, pst)
                        mints.append({"key": mk, "pid": pool_id(b, pst), "lo": _s(b, pst + 160), "hi": _s(b, pst + 192), "liq": _u(b, pst + 224),
                                      "a0max": _u(b, pst + 256), "a1max": _u(b, pst + 288), "owner": b[pst + 332:pst + 352].hex(), "liq_off": pst + 224, "lo_off": pst + 160})
                out["mints"] = mints
        if "key" not in out:
            return None
        return out
    except (ValueError, IndexError):
        return None


# ---- the 1,444-byte layout: absolute byte offsets in the calldata (selector included)
OFF = {
    "selector": (0, 4),            # ac9650d8 multicall(bytes[])
    "n_calls": (36, 68),           # = 2
    "call0_len": (132, 164),       # = 0xc4 (196): initializePool
    "init_sel": (164, 168),        # f7020405 initializePool(PoolKey,uint160)
    "currency0": (180, 200),       # address in word [168, 200)
    "currency1": (212, 232),       # the token; word [200, 232)
    "fee": (232, 264),
    "tick_spacing": (264, 296),
    "hooks": (308, 328),           # word [296, 328)
    "key": (168, 328),             # keccak of these 160 bytes = the pool id
    "sqrt_p": (328, 360),
    "call1_len": (388, 420),       # = 0x3e4 (996): modifyLiquidities
    "modliq_sel": (420, 424),      # dd46508f modifyLiquidities(bytes,uint256)
    "deadline": (456, 488),
    "n_actions": (584, 616),       # = 3
    "actions": (616, 619),         # 02 0d 14: MINT_POSITION, SETTLE_PAIR, SWEEP
    "mint_key": (808, 968),        # the PoolKey again (must equal "key")
    "tick_lower": (968, 1000),
    "tick_upper": (1000, 1032),
    "liquidity": (1032, 1064),
    "amount0_max": (1064, 1096),
    "amount1_max": (1096, 1128),
    "owner": (1140, 1160),         # word [1128, 1160)
}


def decode_1444(data):
    """fixed-offset fast path: None unless every structural word matches the 1,444-byte initializePool + mint layout"""
    b = bytes(data)
    if len(b) != 1444 or b[0:4] != SEL_MULTICALL or _u(b, 4) != 0x20 or _u(b, 36) != 2 or _u(b, 68) != 0x40 or _u(b, 100) != 0x140 \
            or _u(b, 132) != 0xc4 or b[164:168] != SEL_INIT or _u(b, 388) != 0x3e4 or b[420:424] != SEL_MODLIQ or _u(b, 584) != 3 \
            or b[616:619] != bytes([A_MINT, A_SETTLE_PAIR, A_SWEEP]) or b[808:968] != b[168:328]:
        return None
    lo = _s(b, 968); hi = _s(b, 1000)
    return {"key": _key(b, 168), "pid": pool_id(b, 168), "sqrt_p": _u(b, 328), "deadline": _u(b, 456), "lo": lo, "hi": hi, "liq": _u(b, 1032),
            "a0max": _u(b, 1064), "a1max": _u(b, 1096), "owner": b[1140:1160].hex()}


# ---- tick of a sqrtPriceX96 (TickMath.getTickAtSqrtPrice, exact by bisection on getSqrtPriceAtTick)
def sqrt_at_tick(tick):
    a = abs(tick)
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 0x1 else 0x100000000000000000000000000000000
    for bit, m in ((0x2, 0xfff97272373d413259a46990580e213a), (0x4, 0xfff2e50f5f656932ef12357cf3c7fdcc), (0x8, 0xffe5caca7e10e4e61c3624eaa0941cd0),
                   (0x10, 0xffcb9843d60f6159c9db58835c926644), (0x20, 0xff973b41fa98c081472e6896dfb254c0), (0x40, 0xff2ea16466c96a3843ec78b326b52861),
                   (0x80, 0xfe5dee046a99a2a811c461f1969c3053), (0x100, 0xfcbe86c7900a88aedcffc83b479aa3a4), (0x200, 0xf987a7253ac413176f2b074cf7815e54),
                   (0x400, 0xf3392b0822b70005940c7a398e4b70f3), (0x800, 0xe7159475a2c29b7443b29c7fa6e889d9), (0x1000, 0xd097f3bdfd2022b8845ad8f792aa5825),
                   (0x2000, 0xa9f746462d870fdf8a65dc1f90e061e5), (0x4000, 0x70d869a156d2a1b890bb3df62baf32f7), (0x8000, 0x31be135f97d08fd981231505542fcfa6),
                   (0x10000, 0x9aa508b5b7a84e1c677de54f3e99bc9), (0x20000, 0x5d6af8dedb81196699c329225ee604), (0x40000, 0x2216e584f5fa1ea926041bedfe98),
                   (0x80000, 0x48a170391f7dc42444e8fa2)):
        if a & bit:
            r = (r * m) >> 128
    if tick > 0:
        r = ((1 << 256) - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)


def tick_at_sqrt(sp):
    lo, hi = -887272, 887272
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sqrt_at_tick(mid) <= sp: lo = mid
        else: hi = mid - 1
    return lo


def active_liquidity(dec, tick0):
    """the liquidity a buy meets first (v4math.active_liquidity's rule: lo < tick0 <= hi) from the decoded mint(s) on this pool"""
    if "mints" in dec:
        return sum(m["liq"] for m in dec["mints"] if m["pid"] == dec["pid"] and m["lo"] < tick0 <= m["hi"])
    return dec["liq"] if dec["lo"] < tick0 <= dec["hi"] else 0


if __name__ == "__main__":
    import os, sys, json, pickle, collections
    HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE)
    T_INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"; T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
    W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
    sg = lambda x: x - (1 << 256) if x >> 255 else x
    R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))}
    INIT = {l["topics"][1]: l for l in pickle.load(open(os.path.join(SCR, "others", "cache_inits.pkl"), "rb"))["logs"]}
    PL = pickle.load(open(os.path.join(SCR, "others", "cache_plogs.pkl"), "rb"))
    TX = pickle.load(open(os.path.join(HERE, "cache_launch.pkl"), "rb"))
    fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
    stats = collections.Counter(); bad = []; shown = 0; rows = []
    for pid, r in R.items():
        t = TX.get(r["tx"])
        if t is None:
            continue
        data = bytes.fromhex(t["input"][2:]); g = decode_launch(data); f = decode_1444(data)
        il = INIT[pid]; d = il["data"]
        want = {"pid": pid, "currency0": il["topics"][2][-40:], "currency1": il["topics"][3][-40:], "fee": W(d, 0), "tick_spacing": sg(W(d, 1)), "hooks": d[2 + 128 + 24: 2 + 192],
                "sqrt_p": W(d, 3), "tick": sg(W(d, 4))}
        kind = "v3.0" if fam(r) else ("pm1444" if r["inlen"] == 1444 else "pm_other")
        stats[(kind, "n")] += 1
        if g is None:
            stats[(kind, "generic_none")] += 1; continue
        # a multi-pool tx: pick the initializePool for this pid (generic decoder takes the first; check it matches or count as multi)
        if g["pid"] != pid:
            stats[(kind, "generic_other_pool_in_tx")] += 1; continue
        got = {"pid": g["pid"], **g["key"], "sqrt_p": g["sqrt_p"]}
        mm = {k: (got[k], want[k]) for k in ("pid", "currency0", "currency1", "fee", "tick_spacing", "hooks", "sqrt_p") if got[k] != want[k]}
        tk = tick_at_sqrt(g["sqrt_p"])
        if tk != want["tick"]: mm["tick"] = (tk, want["tick"])
        # liquidity vs the launch tx's ModifyLiquidity log on this pool
        mls = [(sg(int(x[4][2:66], 16)), sg(int(x[4][66:130], 16)), sg(int(x[4][130:194], 16))) for x in PL.get(pid, []) if x[2] == T_ML and x[5] == r["tx"]]
        dm = [(m["lo"], m["hi"], m["liq"]) for m in g.get("mints", []) if m["pid"] == pid]
        if PL.get(pid) is not None and sorted(dm) != sorted(mls): mm["mint_vs_ML"] = (dm, mls)
        al = active_liquidity(g, want["tick"])
        if r.get("liq") is not None and al != r["liq"]: mm["active_liq_vs_census"] = (al, r["liq"])
        if f is not None:
            stats[(kind, "fast_ok")] += 1
            fg = {"pid": f["pid"], **f["key"], "sqrt_p": f["sqrt_p"]}
            if fg != got or (f["lo"], f["hi"], f["liq"]) != dm[0]: mm["fast_vs_generic"] = True
        if mm:
            stats[(kind, "mismatch")] += 1; bad.append((kind, pid, r["tx"], mm))
        else:
            stats[(kind, "ok")] += 1
        if kind == "v3.0":
            rows.append({"pid": pid, "tx": r["tx"], "b0": r["b0"], "token": g["key"]["currency1"], "sqrt_p": g["sqrt_p"], "tick": want["tick"], "liq": dm[0][2] if dm else None,
                         "lo": dm[0][0] if dm else None, "hi": dm[0][1] if dm else None, "deadline": g.get("deadline"), "actions": g.get("actions"), "owner_is_from": (g["mints"][0]["owner"] == t["from"][2:].lower()) if g.get("mints") else None,
                         "a0max": g["mints"][0]["a0max"] if g.get("mints") else None, "a1max": g["mints"][0]["a1max"] if g.get("mints") else None, "fast": f is not None, "ok": not mm})
            if shown < 10:
                shown += 1
                print(f"v3.0 {r['tx'][:12]} b0 {r['b0']} pid {pid[:14]} == {g['pid'][:14]} token 0x{g['key']['currency1'][:10]} fee {g['key']['fee']} ts {g['key']['tick_spacing']} "
                      f"sqrtP {g['sqrt_p']} (log {want['sqrt_p']}) tick {tk} (log {want['tick']}) mint [{dm[0][0]},{dm[0][1]}] L {dm[0][2]} (ML log {mls[0][2] if mls else None}) "
                      f"fast {'same' if f else None} -> {'OK' if not mm else mm}")
    print()
    for k in sorted(stats): print(f"{k[0]:9s} {k[1]:26s} {stats[k]}")
    print("mismatches", len(bad))
    for x in bad[:12]: print("  ", x[0], x[1][:14], x[2][:14], str(x[3])[:300])
    json.dump({"stats": {f"{a}|{b}": v for (a, b), v in stats.items()}, "bad": bad[:200], "v3_rows": rows}, open(os.path.join(HERE, "launch_decode.json"), "w"), indent=0)
