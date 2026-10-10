"""Launcher 0x3194e326 runtime: section boundaries, selectors, access-control opcodes in the launcher's own code (bytes 0..3607), revert strings; diff vs copy."""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from disasm import dis
from eth_utils import keccak
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/"
a = bytes.fromhex(open(S + "code_0x3194e326.hex").read().strip()[2:]); b = bytes.fromhex(open(S + "code_0x816d73e4.hex").read().strip()[2:])
print("launcher runtime", len(a), "bytes; sections: launcher code 0-3607 (INVALID at 3607), embedded token initcode 3608-5128, token runtime 5129-6845, token CBOR 6846-6930, launcher CBOR 6931-6983")
SIG = {"2fcb9108": "launch(bytes32 salt,string name,string symbol,string uri,uint256 supply,uint256 tokenAmount,uint24 fee,int24 tickSpacing,uint160 sqrtPriceX96,int24 tickLower,int24 tickUpper,uint256 liquidity,address recipient) payable",
       "54bc5062": "predictTokenAddress(bytes32,string,string,string,uint256) view", "dc4c90d3": "poolManager() view", "791b98bc": "positionManager() view", "12261ee7": "permit2() view"}
for s, n in SIG.items(): assert ("PUSH4", s) in [(x[1], x[2]) for x in dis(a[:120].hex())], s; print("  selector", s, n)
own = [x for x in dis(a.hex()) if x[0] < 3608]
c = collections.Counter(n for _, n, _ in own)
print("opcodes in the launcher's own code:", {k: c[k] for k in ["CALLER", "ORIGIN", "SLOAD", "SSTORE", "TLOAD", "TSTORE", "DELEGATECALL", "SELFDESTRUCT", "CALL", "STATICCALL", "CREATE2", "LOG4"]})
print("PUSH20/32 constants in launcher code:", sorted({x[2][-40:] for x in own if x[1] in ("PUSH32", "PUSH20") and x[2].startswith("000000000000000000000000")}))
print("address 0x01 (ecrecover) referenced as call target? -> STATICCALLs at", [pc for pc, n, _ in own if n == "STATICCALL"], "(nextTokenId on PositionManager, balanceOf on token)")
d = [i for i in range(len(a)) if a[i] != b[i]]
print("copy 0x816d73e4 (hash %s) vs original (hash %s): %d differing bytes, all in %s" % (keccak(b).hex()[:8], keccak(a).hex()[:8], len(d), sorted({(6856 if i < 6900 else 6941) for i in d})), "= the two solc metadata (ipfs) hashes")
