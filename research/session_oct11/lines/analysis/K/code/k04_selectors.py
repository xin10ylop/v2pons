"""dispatcher selectors (PUSH4 x; EQ) and event topics (PUSH32) from the bytecodes; match against a list of plausible signatures."""
import json, re, itertools
from krpc import *
C = json.load(open(os.path.join(DATA, "codes.json")))

def scan(code):
    b = bytes.fromhex(code[2:]); i = 0; sels = []; p32 = []
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f; v = b[i + 1:i + 1 + n]
            if n == 4 and i + 1 + n < len(b) and b[i + 1 + n] == 0x14: sels.append(v.hex())   # PUSH4 x EQ
            if n == 4 and i + 1 + n + 1 < len(b) and b[i + 1 + n] in (0x81, 0x80) and b[i + 2 + n] == 0x14: sels.append(v.hex())
            if n == 32: p32.append(v.hex())
            i += 1 + n
        else: i += 1
    return sorted(set(sels)), sorted(set(p32))

names = ["buy", "sell", "buyTokens", "sellTokens", "buyExactIn", "sellExactIn", "buyExactOut", "swap", "getReserves", "reserves", "virtualEthReserves",
         "virtualTokenReserves", "realEthReserves", "realTokenReserves", "token", "factory", "owner", "creator", "graduated", "complete", "completed",
         "migrate", "graduate", "isGraduated", "isComplete", "feeBps", "fee", "tradingFee", "getAmountOut", "getAmountIn", "quoteBuy", "quoteSell",
         "getBuyPrice", "getSellPrice", "price", "currentPrice", "getPrice", "targetEth", "graduationThreshold", "migrationThreshold", "initialize",
         "init", "progress", "quoteToken", "pool", "poolKey", "hook", "lock", "locked", "unlock", "name", "symbol", "decimals", "totalSupply",
         "balanceOf", "transfer", "approve", "transferFrom", "allowance", "createToken", "create", "createCurve", "launch", "createAndBuy",
         "renounceOwnership", "transferOwnership", "acceptOwnership", "pendingOwner", "setFee", "setFeeTo", "feeTo", "feeRecipient", "treasury",
         "withdraw", "pause", "unpause", "paused", "previewBuy", "previewSell", "calcBuy", "calcSell", "estimateBuy", "estimateSell",
         "ethReserve", "tokenReserve", "getState", "state", "status", "phase", "router", "positionManager", "poolManager", "WETH", "weth",
         "maxBuy", "maxWallet", "startTime", "launchTime", "createdAt", "deadline", "curveFor", "curves", "tokenToCurve", "allCurves", "curvesLength",
         "getCurve", "implementation", "permit2", "collectFees", "claimFees", "claim", "creatorFee", "protocolFee", "creatorFeeBps", "protocolFeeBps",
         "totalRaised", "raised", "ethRaised", "tokensSold", "soldSupply", "sold", "k", "K", "a", "b", "slope", "basePrice", "initialPrice",
         "graduationMarketCap", "marketCap", "getMarketCap", "liquidityLocker", "locker", "migrator", "lpLocker", "tokenOut", "amountOut"]
argsets = ["", "uint256", "uint256,uint256", "address", "address,uint256", "address,uint256,uint256", "uint256,address", "uint256,uint256,address",
           "address,uint256,uint256,uint256", "bool", "address,address", "uint256,uint256,uint256", "address,uint256,address", "address,address,uint256",
           "uint256,uint256,address,uint256", "address,address,uint256,uint256", "uint256,address,uint256", "bytes", "bytes32", "address,bool"]
D = {}
for n in names:
    for a in argsets:
        D[sel(f"{n}({a})")] = f"{n}({a})"
res = {}
for k, v in C.items():
    s, p = scan(v["code"])
    res[k] = {"selectors": {x: D.get(x) for x in s}, "push32": p}
    print(k, v["len"], len(s))
    for x in s: print("   ", x, D.get(x))
json.dump(res, open(os.path.join(OUT, "k04_selectors.json"), "w"), indent=1)
