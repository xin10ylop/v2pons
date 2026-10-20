"""decode launcher launch(0x2fcb9108) calldata"""
from eth_abi import decode
TYPES = ["bytes32", "string", "string", "string", "uint256", "uint256", "uint24", "int24", "address", "int24", "int24", "uint256", "address"]
NAMES = ["salt", "name", "symbol", "s3", "u84", "ua4", "fee", "tickSpacing", "hooks", "tickLower", "tickUpper", "u164", "recipient"]
def dec(inp):
    b = bytes.fromhex(inp[10:])
    try: v = decode(TYPES, b)
    except Exception as e: return {"err": str(e)[:80]}
    return dict(zip(NAMES, [x.hex() if isinstance(x, bytes) else x for x in v]))
if __name__ == "__main__":
    import json, sys
    d = json.load(open("../launcher_txs.json"))
    for h, t in list(d.items())[-3:] + list(d.items())[:2]:
        print(h, t["from"], t["nonce"], t["value"] / 1e18, t["input"][:10], len(t["input"]) // 2 - 1)
        print("   ", dec(t["input"]))
