"""Step 11: the token code (one template?), its public functions, name/symbol/supply/owner, and the launchers' state now
(nonce, balance). Read-only eth_getCode / eth_call / eth_getTransactionCount / eth_getBalance."""
import collections, re
from common import *
from eth_utils import keccak
pools = load_pools()
toks = [p["token"] for p in pools]; lau = [p["launcher"] for p in pools]
codes = rpc.batch("eth_getCode", [[t, "latest"] for t in toks], n=10)
def h(c): return keccak(bytes.fromhex(c[2:])).hex()[:16] if c and c != "0x" else "none"
# strip immutables/metadata: compare by the set of PUSH4 selectors and code length
def push4s(c):
    b = bytes.fromhex(c[2:]); i = 0; out = set()
    while i < len(b):
        op = b[i]
        if op == 0x63 and i + 4 < len(b): out.add(b[i+1:i+5].hex())
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return out
groups = collections.Counter((h(c), (len(c) - 2) // 2) for c in codes)
print("token code groups (hash, bytes):", groups.most_common(8))
sels = [push4s(c) for c in codes]
common_sel = set.intersection(*sels) if sels else set()
NAMES = ["name()", "symbol()", "decimals()", "totalSupply()", "balanceOf(address)", "transfer(address,uint256)", "allowance(address,address)",
         "approve(address,uint256)", "transferFrom(address,address,uint256)", "owner()", "renounceOwnership()", "transferOwnership(address)",
         "increaseAllowance(address,uint256)", "decreaseAllowance(address,uint256)", "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",
         "nonces(address)", "DOMAIN_SEPARATOR()", "eip712Domain()", "burn(uint256)", "burnFrom(address,uint256)", "mint(address,uint256)",
         "setFee(uint256)", "setTax(uint256)", "setTaxes(uint256,uint256)", "blacklist(address)", "setBlacklist(address,bool)", "setBots(address[],bool)",
         "enableTrading()", "openTrading()", "setMaxWallet(uint256)", "setMaxTx(uint256)", "excludeFromFees(address,bool)", "pause()", "unpause()",
         "paused()", "setPair(address)", "setPool(address)", "setTradingEnabled(bool)", "launch()", "manager()", "admin()", "getOwner()",
         "initialize(string,string,uint256)", "setWhitelist(address,bool)", "multicall(bytes[])", "PERMIT_TYPEHASH()", "version()"]
known = {keccak(text=n).hex()[:8]: n for n in NAMES}
print("PUSH4 constants in every token's code:", len(common_sel))
print("  known:", sorted(known[s] for s in common_sel if s in known))
print("  unknown:", sorted(s for s in common_sel if s not in known))
calls = []
for t in toks:
    for sig in ("name()", "symbol()", "decimals()", "totalSupply()", "owner()"):
        calls.append([{"to": t, "data": "0x" + keccak(text=sig).hex()[:8]}, "latest"])
res = rpc.batch("eth_call", calls, n=25)
def dstr(x):
    try:
        b = bytes.fromhex(x[2:]); off = int.from_bytes(b[:32], "big"); ln = int.from_bytes(b[off:off+32], "big"); return b[off+32:off+32+ln].decode(errors="replace")
    except Exception: return None
info = []
for i, t in enumerate(toks):
    r = res[5*i:5*i+5]
    info.append(dict(token=t, name=dstr(r[0]), symbol=dstr(r[1]), dec=int(r[2], 16) if r[2] and r[2] != "0x" else None,
                     supply=int(r[3], 16) / 1e18 if r[3] and r[3] != "0x" else None, owner=("0x" + r[4][-40:]) if r[4] and len(r[4]) >= 66 else r[4]))
print("decimals", collections.Counter(x["dec"] for x in info), "supply", collections.Counter(x["supply"] for x in info).most_common(3))
print("owner()", collections.Counter((x["owner"] == p["launcher"]) if x["owner"] and x["owner"].startswith("0x") and len(x["owner"]) == 42 else x["owner"] for x, p in zip(info, pools)).most_common(4))
print("names (first 12):", [(x["name"], x["symbol"]) for x in info[:12]])
st = rpc.batch("eth_getTransactionCount", [[a, "latest"] for a in lau], n=25)
bal = rpc.batch("eth_getBalance", [[a, "latest"] for a in lau], n=25)
print("launcher nonce now:", collections.Counter(int(x, 16) for x in st).most_common(6))
bl = sorted(int(x, 16) / 1e18 for x in bal); print("launcher balance now ETH p10/50/90", bl[len(bl)//10], bl[len(bl)//2], bl[9*len(bl)//10])
jdump(dict(info=info, code_groups=[[k[0], k[1], n] for k, n in groups.items()], common_selectors=sorted(common_sel),
           launcher_nonce=[int(x, 16) for x in st], launcher_bal=[int(x, 16) for x in bal]), "s11_tokens.json")
# a representative token's full selector list (for the report)
print("first token selectors:", sorted(known.get(s, s) for s in sels[0]))
print(rpc.STATS)
