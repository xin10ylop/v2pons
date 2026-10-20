"""Read-only chain checks for path (a), all by eth_call / eth_getCode on the public RPC:
1. SwapRouter02 0xcaf681a6 and the PositionManager 0x73991a25 point at the V3 factory and WETH seen in the census;
2. the crowd contracts' code (size, hash): one code behind every address?;
3. one V3-line token's code: its selectors and the opcodes a tax/limit/blacklist would need;
4. a buy of 0.0058 ETH through SwapRouter02 (multicall(deadline, [exactInputSingle]) with ETH value) from a fresh address on a live pool of the
   line, against the single-range prediction (v4math) from the pool's slot0 and liquidity;
5. the sell of those tokens back (multicall(deadline, [exactInputSingle(token->WETH, recipient = the router), unwrapWETH9(min, us)])) with
   the token balance and the router allowance put in place by state override (the approve the sell needs)."""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, "/home/user/v2pons/src")
import rpc, v4math
from eth_utils import keccak
from v3dec import WETH
ROUTER = "0xcaf681a66d020601342297493863e78c959e5cb2"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
CROWD = ["0x80114879f80d156c8003676557324c518babd194", "0xd26c8cfce843f4122753425dd6613d7576777ec8", "0xa28f468cb898cc407c981e26a521dfb2e2774174",
         "0xaf9d6fa019328d8cf8598d0d5be22cc6622b09f1", "0x84021dc22cf77fb6ba5665cf247c743fe05beb7d", "0xfc7241d4356564e32b16e8e4838c648efceb8144",
         "0x71a7629fcc6e69b69d00393af53942a87512a4ee", "0x85ce78329f7449fde7c46658bf646b1cedb59858", "0x7feb3ecbacbd0cc23ec46659d541636d58749a97"]
w = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
sel = lambda s: keccak(text=s).hex()[:8]
def call(to, data, frm=None, value=0, over=None):
    tx = {"to": to, "data": "0x" + data}
    if frm: tx["from"] = frm
    if value: tx["value"] = hex(value)
    return rpc.call("eth_call", [tx, "latest"] + ([over] if over else []))
out = {}
print("1. router factory", call(ROUTER, sel("factory()"))[-40:], "WETH9", call(ROUTER, sel("WETH9()"))[-40:], "| NPM factory", call(NPM, sel("factory()"))[-40:], "WETH9", call(NPM, sel("WETH9()"))[-40:])
codes = rpc.batch("eth_getCode", [[a, "latest"] for a in CROWD])
print("2. crowd contracts:")
for a, c in zip(CROWD, codes):
    print(f"   {a} size {(len(c) - 2) // 2} hash {keccak(bytes.fromhex(c[2:])).hex()[:16]}")
D = json.load(open("w05_recent_8h.json")); F = json.load(open("w05_recent_8h_forward.json"))
live = [z for z in F if z["pull"] is None][0]; x = [y for y in D["line"] if y["pool"] == live["pool"]][0]
pool = x["pool"]; token = x["token1"] if x["token0"] == "0x" + WETH else x["token0"]
code = rpc.call("eth_getCode", [token, "latest"]); b = bytes.fromhex(code[2:])
SIGS = ["transfer(address,uint256)", "transferFrom(address,address,uint256)", "approve(address,uint256)", "balanceOf(address)", "totalSupply()", "allowance(address,address)",
        "name()", "symbol()", "decimals()", "owner()", "burn(uint256)", "burnFrom(address,uint256)", "increaseAllowance(address,uint256)", "decreaseAllowance(address,uint256)"]
LBL = {sel(s): s for s in SIGS}
n_meta = int.from_bytes(b[-2:], "big"); core = b[:-n_meta - 2] if n_meta + 2 < len(b) and b[-n_meta - 2] in (0xa1, 0xa2) else b
sels = []; ops = {}; i = 0; b_all = b; b = core
while i < len(b):
    op = b[i]
    if op == 0x63 and i + 5 <= len(b): sels.append(b[i + 1:i + 5].hex())
    if op in (0x42, 0x43, 0x32, 0xf1, 0xfa, 0xf4, 0xff, 0xf0, 0xf5, 0x3a, 0x31, 0x47): ops[op] = ops.get(op, 0) + 1
    i += 1 + (op - 0x5f if 0x60 <= op <= 0x7f else 0)
print(f"3. token {token} code {len(b_all)} bytes ({len(b)} without metadata); PUSH4 constants: {[LBL.get(s, s) for s in dict.fromkeys(sels)]}; risky opcodes {ops}")
# 4. the buy
ME = "0x" + "5e" * 20; Q = int(0.0058e18)
s0 = call(pool, sel("slot0()")); sp = int(s0[2:66], 16); L = int(call(pool, sel("liquidity()")), 16)
tick = int(s0[66:130], 16); tick = tick - (1 << 256) if tick >> 255 else tick
pred = v4math.buy_out_int(sp, L, Q, 100) if x["token0"] == "0x" + WETH else None
exact = sel("exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))")
def mc(deadline, calls):
    n = len(calls); head = w(deadline) + w(64) + w(n); offs = []; body = ""; off = 32 * n
    for c in calls:
        cb = bytes.fromhex(c); offs.append(w(off)); pad = (32 - len(cb) % 32) % 32
        body += w(len(cb)) + cb.hex() + "00" * pad; off += 32 + len(cb) + pad
    return sel("multicall(uint256,bytes[])") + head + "".join(offs) + body
deadline = int(time.time()) + 600
buy_inner = exact + w(WETH) + w(token) + w(100) + w(ME) + w(Q) + w(0) + w(0)
buy = mc(deadline, [buy_inner])
over = {ME: {"balance": hex(10 ** 18)}}
r = call(ROUTER, buy, ME, Q, over)
# multicall returns bytes[]: offset, n, offset0, len0, data0 (amountOut)
got = int(r[2 + 64 * 4: 2 + 64 * 5], 16)
print(f"4. pool {pool} slot0 sqrtP {sp} tick {tick} liquidity {L}; buy 0.0058 ETH via SwapRouter02 (value, {len(bytes.fromhex(buy)) + 0} B calldata): out {got} vs single-range prediction {pred} (diff {((got - pred) / pred) if pred else None})")
# 5. the sell: find the balance and allowance slots (OZ layout first), then sell `got` tokens back
bal_slot = None
for s in range(0, 8):
    k = keccak(bytes.fromhex(w(ME) + w(s))).hex()
    v = call(token, sel("balanceOf(address)") + w(ME), None, 0, {token: {"stateDiff": {"0x" + k: "0x" + w(got)}}})
    if int(v, 16) == got: bal_slot = s; break
alw_slot = None
for s in range(0, 8):
    k = keccak(bytes.fromhex(w(ROUTER) + keccak(bytes.fromhex(w(ME) + w(s))).hex())).hex()
    v = call(token, sel("allowance(address,address)") + w(ME) + w(ROUTER), None, 0, {token: {"stateDiff": {"0x" + k: "0x" + w((1 << 256) - 1)}}})
    if int(v, 16) == (1 << 256) - 1: alw_slot = s; break
print(f"5. token storage: balances at slot {bal_slot}, allowances at slot {alw_slot}")
if bal_slot is not None and alw_slot is not None:
    kb = "0x" + keccak(bytes.fromhex(w(ME) + w(bal_slot))).hex(); ka = "0x" + keccak(bytes.fromhex(w(ROUTER) + keccak(bytes.fromhex(w(ME) + w(alw_slot))).hex())).hex()
    sell_inner = exact + w(token) + w(WETH) + w(100) + w(2) + w(got) + w(0) + w(0)
    unwrap = sel("unwrapWETH9(uint256,address)") + w(0) + w(ME)
    sell = mc(deadline, [sell_inner, unwrap])
    o2 = {ME: {"balance": hex(10 ** 16)}, token: {"stateDiff": {kb: "0x" + w(got), ka: "0x" + w((1 << 256) - 1)}}}
    r2 = call(ROUTER, sell, ME, 0, o2)
    eth_back = int(r2[2 + 64 * 5: 2 + 64 * 6], 16)
    print(f"   sell {got} tokens via multicall(deadline,[exactInputSingle -> router, unwrapWETH9]) ({len(bytes.fromhex(sell))} B): {eth_back} wei back = {(eth_back - Q) / Q:+.4%} round trip "
          f"(the sell is priced on today's pool, without our buy in it); prediction on the same state {v4math.sell_out_int(sp, L, got, 100)}; "
          f"after our buy (the real round trip) {v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L, Q - (Q*100 + 999999)//10**6)), L, got, 100)} = {(v4math.sell_out_int(int(v4math.sqrt_after_buy(sp, L, Q - (Q*100 + 999999)//10**6)), L, got, 100) - Q) / Q:+.4%}")
    # 5b: the same sell without the allowance: it must revert (the approve is required)
    o3 = {ME: {"balance": hex(10 ** 16)}, token: {"stateDiff": {kb: "0x" + w(got)}}}
    try:
        call(ROUTER, sell, ME, 0, o3); print("   without the allowance: did NOT revert (unexpected)")
    except RuntimeError as e:
        print("   without the allowance: reverts:", str(e)[:160])
    # approve's own gas: eth_estimateGas is not in the allowed list; the approve is a plain OZ approve (one SSTORE): ~46k gas
print(rpc.STATS)
