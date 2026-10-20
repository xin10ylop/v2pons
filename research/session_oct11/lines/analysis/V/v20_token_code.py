"""C-1 token template: eth_getCode of a live post-census C-1 token and of a census C-1 token; their skeleton hash (opcodes without push
data, metadata stripped) against the census key cb79985d; the dispatcher's selectors, labelled from a list of common ERC-20 and
honeypot/tax/limit signatures; opcodes that tax/limit logic needs (TIMESTAMP, NUMBER, ORIGIN, CALL/STATICCALL/DELEGATECALL, SELFDESTRUCT);
PUSH20 constants (hard-coded addresses). Codes saved to token_<addr>.hex."""
import rpc
from common import *
from eth_utils import keccak
F = json.load(open(os.path.join(V, "fresh.json")))["c1"]
live = [x for x in F if not x["pulls"]]
rows = [r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"]
toks = [live[0]["token"], rows[len(rows) // 2]["token"]]
SIGS = ["transfer(address,uint256)", "transferFrom(address,address,uint256)", "approve(address,uint256)", "balanceOf(address)", "totalSupply()", "allowance(address,address)",
        "name()", "symbol()", "decimals()", "owner()", "renounceOwnership()", "transferOwnership(address)", "increaseAllowance(address,uint256)", "decreaseAllowance(address,uint256)",
        "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)", "nonces(address)", "DOMAIN_SEPARATOR()", "eip712Domain()", "burn(uint256)", "burnFrom(address,uint256)", "mint(address,uint256)",
        "setFee(uint256)", "setFees(uint256,uint256)", "setTaxes(uint256,uint256)", "setBuyFee(uint256)", "setSellFee(uint256)", "excludeFromFees(address,bool)", "excludeFromFee(address)",
        "blacklist(address)", "setBlacklist(address,bool)", "addBots(address[])", "setBots(address[],bool)", "isBot(address)", "delBot(address)", "removeLimits()", "setMaxWallet(uint256)",
        "setMaxTxAmount(uint256)", "enableTrading()", "openTrading()", "setTradingEnabled(bool)", "manualSwap()", "manualswap()", "manualsend()", "setSwapEnabled(bool)", "setCooldown(bool)",
        "pause()", "unpause()", "paused()", "setPair(address)", "setRouter(address)", "uniswapV2Pair()", "uniswapV2Router()", "_maxWalletSize()", "_maxTxAmount()", "maxWallet()",
        "initialize(string,string,uint256)", "initialize(string,string,uint256,address)", "decimals()", "version()", "tokenURI()", "setMetadata(string)", "creator()", "factory()", "pool()",
        "multicall(bytes[])", "supportsInterface(bytes4)", "transferAndCall(address,uint256,bytes)", "setWhitelist(address,bool)", "whitelist(address)", "setLimits(uint256,uint256)",
        "launch()", "launched()", "tradingOpen()", "limitsInEffect()", "hook()", "poolId()", "rescue(address)", "withdraw()", "sweep(address)"]
LBL = {keccak(text=s).hex()[:8]: s for s in SIGS}
OPN = {0x42: "TIMESTAMP", 0x43: "NUMBER", 0x32: "ORIGIN", 0xf1: "CALL", 0xfa: "STATICCALL", 0xf4: "DELEGATECALL", 0xff: "SELFDESTRUCT", 0xf0: "CREATE", 0xf5: "CREATE2", 0x3a: "GASPRICE", 0x31: "BALANCE", 0x47: "SELFBALANCE", 0x5a: "GAS"}
def strip_meta(b):
    if len(b) > 2:
        n = int.from_bytes(b[-2:], "big")
        if n + 2 < len(b) and b[-n - 2] in (0xa1, 0xa2): return b[:-n - 2]
    return b
def disasm(b):
    i = 0; out = []
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f; out.append((i, op, b[i + 1:i + 1 + n])); i += 1 + n
        else: out.append((i, op, b"")); i += 1
    return out
for a in toks:
    code = rpc.call("eth_getCode", [a, "latest"]); b = bytes.fromhex(code[2:]); open(os.path.join(V, f"token_{a}.hex"), "w").write(code)
    core = strip_meta(b); ins = disasm(core)
    skel = keccak(bytes(op for _, op, _ in ins)).hex()
    sels = []
    for k, (i, op, d) in enumerate(ins):
        if op == 0x63 and k + 2 < len(ins) and ins[k + 1][1] in (0x14, 0x81, 0x82, 0x80) or (op == 0x63 and k + 1 < len(ins) and ins[k + 1][1] == 0x14): sels.append(d.hex())
    sels = sorted(set(sels))
    ops = C.Counter(OPN[op] for _, op, _ in ins if op in OPN)
    p20 = sorted({d.hex() for _, op, d in ins if op == 0x73})
    print(f"token {a}: code {len(b)} bytes; skeleton {skel[:16]} (census key cb79985d: {'match' if skel.startswith('cb79985d') else 'NO MATCH'})")
    print(f"  dispatcher selectors ({len(sels)}): " + ", ".join(f"{s}={LBL.get(s, '?')}" for s in sels))
    print(f"  opcodes of interest: {dict(ops)}; PUSH20 constants: {p20}")
print(rpc.STATS)
