"""ur: the calldata the operator's crowd sends. Its buys and its fleet's sells all go through the Uniswap Universal Router on
Robinhood Chain (0x8876...0904), one V4_SWAP command with three actions (SWAP_EXACT_IN_SINGLE, SETTLE_ALL, TAKE_ALL), no hook
data, no price limit, a deadline of 2^256-1; a sell is prepared by two approvals, the token to Permit2 (unlimited) and Permit2 to
the router (unlimited, never expiring). The engine sends the same bytes from its own wallet, so in the pool's Swap event our buy
carries the router as its sender like every buy the pool has seen, and the transaction itself has the crowd's shape (to, selector,
commands, actions, layout). Only the wallet, the amounts and the deadline differ.

The layouts here reproduce two real transactions byte for byte (tests/test_ur.py): a crowd buy and a fleet sell on the operator's
sub-1% pools of Oct 7-8. The router's ExactInputSingleParams has the sqrtPriceLimitX96 field (an older v4-periphery build), so
the struct's head is ten words, not nine. Everything is hand-encoded; no ABI library.
"""
from eth_utils import keccak

UR = "0x8876789976decbfcbbbe364623c63652db8c0904"              # Universal Router on Robinhood Chain (chain 4663)
PERMIT2 = "0x000000000022d473030f116ddee9f6b43ac78ba3"         # canonical Permit2, 9152 bytes of code on the chain
SEL_EXECUTE = "3593564c"                                       # execute(bytes,bytes[],uint256)
SEL_APPROVE = "095ea7b3"                                       # approve(address,uint256)
SEL_PERMIT2_APPROVE = "87517c45"                               # Permit2.approve(address token,address spender,uint160 amount,uint48 expiration)
CMD_V4_SWAP = 0x10
ACT_SWAP_EXACT_IN_SINGLE = 0x06; ACT_SETTLE_ALL = 0x0c; ACT_TAKE_ALL = 0x0f
MAX256 = (1 << 256) - 1; MAX160 = (1 << 160) - 1; MAX48 = (1 << 48) - 1; MAX128 = (1 << 128) - 1
T_TRANSFER = keccak(text="Transfer(address,address,uint256)").hex()
T_SWAP = keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
word = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)


def _bytes_arg(hexstr):
    """one ABI `bytes` value: its length word and its content padded to 32 bytes"""
    n = len(hexstr) // 2
    return word(n) + hexstr + "0" * ((-len(hexstr)) % 64)


def _bytes_array(items):
    """one ABI `bytes[]` value: the count, the offsets of the items (from the first offset word), then each item"""
    heads = []; off = 32 * len(items)
    for it in items:
        heads.append(word(off)); off += len(_bytes_arg(it)) // 2
    return word(len(items)) + "".join(heads) + "".join(_bytes_arg(it) for it in items)


def exact_in_single_params(key, zero_for_one, amount_in, min_out):
    """abi.encode(ExactInputSingleParams(poolKey, zeroForOne, amountIn, amountOutMinimum, sqrtPriceLimitX96 = 0, hookData = ""))"""
    if not 0 <= amount_in <= MAX128 or not 0 <= min_out <= MAX128:
        raise ValueError("amountIn and amountOutMinimum are uint128")
    return (word(0x20) + word(key["c0"]) + word(key["token"]) + word(key["fee"]) + word(key["tick_spacing"]) + word(key["hooks"])
            + word(1 if zero_for_one else 0) + word(amount_in) + word(min_out) + word(0) + word(0x140) + word(0))


def v4_swap_input(key, zero_for_one, amount_in, min_out):
    """the V4_SWAP command's input: abi.encode(actions, params[]) for one exact-input single swap, settle all of what is owed in the
    input currency (the crowd's limit: unlimited), take all of the output currency (at least min_out)"""
    actions = "%02x%02x%02x" % (ACT_SWAP_EXACT_IN_SINGLE, ACT_SETTLE_ALL, ACT_TAKE_ALL)
    cur_in, cur_out = (key["c0"], key["token"]) if zero_for_one else (key["token"], key["c0"])
    params = [exact_in_single_params(key, zero_for_one, amount_in, min_out), word(cur_in) + word(MAX256), word(cur_out) + word(min_out)]
    return word(0x40) + word(0x80) + _bytes_arg(actions) + _bytes_array(params)


def execute(commands_hex, inputs, deadline):
    """calldata of execute(bytes commands, bytes[] inputs, uint256 deadline); deadline 0 means none (2^256-1, the crowd's value)"""
    return "0x" + SEL_EXECUTE + word(0x60) + word(0xa0) + word(deadline if deadline else MAX256) + _bytes_arg(commands_hex) + _bytes_array(inputs)


def buy_calldata(key, amount_in, min_out, deadline=0):
    """ETH (the transaction's value, amount_in) into the pool for at least min_out tokens, the tokens to the sender"""
    return execute("%02x" % CMD_V4_SWAP, [v4_swap_input(key, True, amount_in, min_out)], deadline)


def sell_calldata(key, amount_in, min_out=0, deadline=0):
    """amount_in tokens (pulled from the sender through Permit2) into the pool for at least min_out wei, the ETH to the sender"""
    return execute("%02x" % CMD_V4_SWAP, [v4_swap_input(key, False, amount_in, min_out)], deadline)


AMOUNT_IN_OFFSET = 4 + 32 * 24         # byte offset of amountIn in buy/sell calldata (word 24 after the selector), for a harness that patches it


def approve_permit2_calldata(amount=MAX256, permit2=PERMIT2):
    """token.approve(Permit2, unlimited): the fleet's first approval before a sell"""
    return "0x" + SEL_APPROVE + word(permit2) + word(amount)


def permit2_approve_calldata(token, spender=UR, amount=MAX160, expiration=MAX48):
    """Permit2.approve(token, router, unlimited, never expiring): the fleet's second approval before a sell"""
    return "0x" + SEL_PERMIT2_APPROVE + word(token) + word(spender) + word(amount) + word(expiration)


def tokens_received(receipt, token, to):
    """what a buy's receipt delivered to `to`: the token's Transfer to it (exact, whatever the pool said), else the Swap's amount1"""
    token = token.lower().replace("0x", ""); to = to.lower().replace("0x", ""); total = 0; seen = False
    for l in receipt.get("logs", []):
        tp = l.get("topics") or []
        if l["address"].lower().replace("0x", "") == token and len(tp) == 3 and tp[0][2:] == T_TRANSFER and tp[2][-40:].lower() == to:
            total += int(l["data"], 16); seen = True
    if seen:
        return total
    for l in receipt.get("logs", []):
        tp = l.get("topics") or []
        if tp and tp[0][2:] == T_SWAP:
            a1 = int(l["data"][2 + 64:2 + 128], 16)
            if a1 >= 1 << 255: a1 -= 1 << 256
            if a1 >= 1 << 127: a1 -= 1 << 128
            return max(a1, 0)
    return 0
