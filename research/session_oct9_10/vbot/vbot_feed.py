#!/usr/bin/env python3
"""What the engine needs to recognise and follow the PM1444 v3.0 "volume bot" family from the sequencer feed, from calldata alone:

  launch_of(to, value, data)   the family's launch (fingerprint below) -> pool dict ready to arm (pid, key, sqrtP, liquidity), else None
  bot_buy(to, value, data)     a buy through the bot's router 0x1cbaf24d (selector c1120e3d, 324 bytes) -> (token, eth_in, min_out, recipient, key)
  ur_swaps(to, value, data)    every V4_SWAP / SWAP_EXACT_IN_SINGLE inside a Universal Router execute (24856bc3 or 3593564c) ->
                               [(key, zero_for_one, amount_in, min_out)]  (the bot's sells: zero_for_one False, value 0)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launch_decode import decode_1444, _u, _s, _key, pool_id

POSITION_MANAGER = "58daec3116aae6d93017baaea7749052e8a04fa7"
UNIVERSAL_ROUTER = "8876789976decbfcbbbe364623c63652db8c0904"
BOT_ROUTER = "1cbaf24d53fe930fce8eff149fa797d2611da149"
POOL_MANAGER = "8366a39cc670b4001a1121b8f6a443a643e40951"
SEL_BOT_BUY = bytes.fromhex("c1120e3d")
SEL_UR_EXEC = bytes.fromhex("24856bc3"); SEL_UR_EXEC_DL = bytes.fromhex("3593564c")
CMD_V4_SWAP = 0x10; A_SWAP_EXACT_IN_SINGLE = 0x06

# the family's constants, every one equal on all 718 census launches (Oct 8 00:00 - Oct 9 14:48)
FAMILY = {
    "to": POSITION_MANAGER, "selector": "ac9650d8", "calldata_len": 1444, "value": 3 * 10**18,
    "fee": 10000, "tick_spacing": 200, "hooks": "0" * 40, "currency0": "0" * 40,
    "tick_lower": -887200, "tick_upper": 887200, "actions": "020d14",
    "sqrt_p": 679394651928963067279918579724198,          # tick 181141
    "liquidity": 25725498245903809899643,
}
TICK0 = 181141


def launch_of(to, value, data, strict=True):
    """the family's launch: to the PositionManager, value 3 ETH, the 1,444-byte initializePool + MINT_POSITION/SETTLE_PAIR/SWEEP layout,
    ETH/token key with fee 1%, tick spacing 200, no hook, full-range mint; strict also pins the launch price and liquidity"""
    if to != POSITION_MANAGER or value != FAMILY["value"] or len(data) != 1444:
        return None
    d = decode_1444(data)
    if d is None:
        return None
    k = d["key"]
    if k["currency0"] != FAMILY["currency0"] or k["fee"] != FAMILY["fee"] or k["tick_spacing"] != FAMILY["tick_spacing"] or k["hooks"] != FAMILY["hooks"] \
            or d["lo"] != FAMILY["tick_lower"] or d["hi"] != FAMILY["tick_upper"]:
        return None
    if strict and (d["sqrt_p"] != FAMILY["sqrt_p"] or d["liq"] != FAMILY["liquidity"]):
        return None
    return {"pid": d["pid"], "c0": k["currency0"], "token": k["currency1"], "token_bytes": bytes.fromhex(k["currency1"]), "fee": k["fee"],
            "tick_spacing": k["tick_spacing"], "hooks": k["hooks"], "sqrt_p": d["sqrt_p"], "liq": d["liq"], "owner": d["owner"], "deadline": d["deadline"]}


def bot_buy(to, value, data):
    """the bot's router call: c1120e3d(address universalRouter, address poolManager, address token, uint256 a, uint256 minOut?, address recipient,
    uint256 deadline, uint24 fee, int24 tickSpacing, address hooks), 324 bytes, ETH as tx.value"""
    if to != BOT_ROUTER or len(data) != 324 or data[:4] != SEL_BOT_BUY:
        return None
    b = data
    return {"ur": b[16:36].hex(), "pm": b[48:68].hex(), "token": b[80:100].hex(), "w3": _u(b, 100), "w4": _u(b, 132), "recipient": b[176:196].hex(),
            "deadline": _u(b, 196), "fee": _u(b, 228), "tick_spacing": _s(b, 260), "hooks": b[304:324].hex(), "eth_in": value}


def _dyn(b, base, pos):
    st = base + _u(b, pos); ln = _u(b, st)
    if st + 32 + ln > len(b): raise ValueError
    return st + 32, ln


def ur_swaps(to, value, data):
    """V4 exact-input single swaps inside a Universal Router execute(bytes commands, bytes[] inputs[, uint256 deadline])"""
    b = bytes(data)
    if to != UNIVERSAL_ROUTER or len(b) < 100 or b[:4] not in (SEL_UR_EXEC, SEL_UR_EXEC_DL):
        return []
    out = []
    try:
        cst, cln = _dyn(b, 4, 4); cmds = b[cst:cst + cln]
        arr = 4 + _u(b, 36); n = _u(b, arr)
        for i in range(min(n, len(cmds))):
            if cmds[i] & 0x3f != CMD_V4_SWAP: continue
            ist, iln = _dyn(b, arr + 32, arr + 32 + 32 * i)            # abi.encode(bytes actions, bytes[] params)
            ast, aln = _dyn(b, ist, ist); acts = b[ast:ast + aln]
            parr = ist + _u(b, ist + 32); pn = _u(b, parr)
            for j in range(min(pn, len(acts))):
                if acts[j] != A_SWAP_EXACT_IN_SINGLE: continue
                pst, pln = _dyn(b, parr + 32, parr + 32 + 32 * j)
                t = pst + _u(b, pst)                                     # the struct is dynamic (hookData): a head offset first
                out.append({"key": _key(b, t), "pid": pool_id(b, t), "zero_for_one": _u(b, t + 160) != 0, "amount_in": _u(b, t + 192), "min_out": _u(b, t + 224)})
    except (ValueError, IndexError):
        return out
    return out


PERMIT2 = "000000000022d473030f116ddee9f6b43ac78ba3"
SEL_BOT_PULL = bytes.fromhex("a0f7978d"); SEL_P2_APPROVE = bytes.fromhex("87517c45"); SEL_NFT_APPROVE = bytes.fromhex("095ea7b3")


def bot_pull(to, value, data):
    """the deployer's pull through the bot router: a0f7978d(address token, address positionManager, address universalRouter, uint256 tokenId,
    uint256 deadline, uint24 fee, int24 tickSpacing, address hooks), 260 bytes, value 0: removes the whole position (seen 10 of 10 in the
    replayed hour; the deployer's nonce = launch nonce + 2)"""
    if to != BOT_ROUTER or len(data) != 260 or data[:4] != SEL_BOT_PULL or value:
        return None
    return {"token": data[16:36].hex(), "pm": data[48:68].hex(), "ur": data[80:100].hex(), "token_id": _u(data, 100), "deadline": _u(data, 132),
            "fee": _u(data, 164), "tick_spacing": _s(data, 196), "hooks": data[240:260].hex()}


def permit2_approve(to, value, data):
    """Permit2.approve(address token, address spender, uint160 amount, uint48 expiration): a bot wallet readying a sell (its sell follows
    3-4 blocks later in most cases)"""
    if to != PERMIT2 or len(data) != 132 or data[:4] != SEL_P2_APPROVE:
        return None
    return {"token": data[16:36].hex(), "spender": data[48:68].hex(), "amount": _u(data, 68), "expiration": _u(data, 100)}


def nft_approve(to, value, data):
    """PositionManager.approve(address spender, uint256 tokenId): the deployer hands the position to the bot router, 4-5 blocks after the launch"""
    if to != POSITION_MANAGER or len(data) != 68 or data[:4] != SEL_NFT_APPROVE:
        return None
    return {"spender": data[16:36].hex(), "token_id": _u(data, 36)}


def sell_sqrt(sp, liq, amount_in, fee):
    """the pool's sqrtPriceX96 after an exact-input sell of `amount_in` tokens (SqrtPriceMath.getNextSqrtPriceFromAmount1RoundingDown, fee
    taken first as SwapMath does): exact on 1,000+ replayed sells"""
    return sp + ((amount_in * (1_000_000 - fee) // 1_000_000) << 96) // liq


def buy_sqrt(sp, liq, eth_in, fee):
    """after an exact-input buy (getNextSqrtPriceFromAmount0RoundingUp)"""
    n1 = liq << 96; x = eth_in * (1_000_000 - fee) // 1_000_000
    return -(-(n1 * sp) // (n1 + x * sp))
