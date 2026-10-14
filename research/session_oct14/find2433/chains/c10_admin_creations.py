"""Contracts created by the router admins (0x5b2b20e1 on Ethereum/Base/BNB, 0x0152c954 on Robinhood): CREATE address per nonce, code length/hash
per chain, and whether the code equals the bot router's with the embedded admin address masked."""
import sys, json; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak, to_checksum_address
import rlp
def create_addr(a, n): return "0x" + keccak(rlp.encode([bytes.fromhex(a[2:]), n])).hex()[-40:]
RH_R = bytes.fromhex(open("code_botrouter.hex").read()[2:])
ADM = {"0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d": ["eth", "base", "bsc", "arb", "uni", "rh"], "0x0152c954397718abfe4716eb3aaf86903cff3796": ["rh", "eth", "base", "bsc", "arb", "uni"]}
def masked(c, adm):
    b = bytes.fromhex(c[2:]); return b.replace(bytes.fromhex(adm[2:]), b"\0" * 20)
ref = masked("0x" + RH_R.hex(), "0x0152c954397718abfe4716eb3aaf86903cff3796")
out = []
for adm, chains in ADM.items():
    for ch in chains:
        n = int(rpcx.call(ch, "eth_getTransactionCount", [adm, "latest"]), 16)
        addrs = [create_addr(adm, i) for i in range(n)]
        codes = rpcx.batch(ch, "eth_getCode", [[a, "latest"] for a in addrs], n=20) if addrs else []
        for i, (a, c) in enumerate(zip(addrs, codes)):
            if c and len(c) > 2:
                same = masked(c, adm) == ref
                row = {"admin": adm, "chain": ch, "nonce": i, "addr": a, "len": (len(c) - 2) // 2, "hash": "0x" + keccak(hexstr=c).hex(), "router_equal_masked": same}
                out.append(row); print(row)
        print(adm[:10], ch, "nonce", n, "contracts", sum(1 for r in out if r["admin"] == adm and r["chain"] == ch))
json.dump(out, open("c10_admin_creations.json", "w"), indent=1)
