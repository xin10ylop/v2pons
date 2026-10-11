"""try plausible event signatures against the observed topics (keccak)."""
import itertools, json
from eth_utils import keccak
T = {"8d4aad49": "create", "ec36bf57": "buy", "8113d738": "sell", "3bc39a55": "surcharge", "9f4cd7c4": "fee claim", "e4b7e48f": "allowlist", "908408e3": "init",
     "cdb72f15": "curve full", "a0a18f5b": "burn at migration", "0a44ef75": "migration", "308c390e": "factory 4-topic", "bd886f85": "factory 3-topic", "c532c43b": "v4 hook fee", "4e45da44": "fee vault", "dcacba5e": "router buy", "85177f28": "fee collector"}
names = ["Buy", "Sell", "Bought", "Sold", "Trade", "Swap", "TokenBought", "TokensBought", "TokensSold", "TokenSold", "Purchase", "Create", "Created", "TokenCreated",
         "CurveCreated", "Launch", "Launched", "TokenLaunched", "Graduated", "Graduate", "Graduation", "Migrated", "Migration", "Complete", "Completed", "CurveCompleted",
         "LiquidityAdded", "PoolCreated", "TokensBurned", "Burn", "Burned", "FeesClaimed", "FeesDistributed", "FeeDistributed", "FeesCollected", "SniperTax", "SnipeTax",
         "SniperFee", "AntiSnipe", "EarlyBuyFee", "LaunchTax", "Whitelisted", "Allowlisted", "Exempt", "ExemptAdded", "Initialized", "CurveInitialized", "Deposit",
         "FeeReceived", "Received", "CreatorFee", "HookFee", "FeeTaken", "Fee", "Fees", "GraduationReady", "ReadyToGraduate", "CurveFilled", "DevBuy", "BundleAllowed", "FeeAccrued", "Claimed", "Distributed"]
types = ["address", "uint256", "bool", "uint128", "int256", "bytes32", "uint24", "int24", "uint160"]
hits = {}
for n in names:
    for k in range(0, 7):
        for combo in itertools.product(["address", "uint256"], repeat=k):
            s = f"{n}({','.join(combo)})"; h = keccak(text=s).hex()[:8]
            if h in T: hits[h] = s
for h, s in hits.items(): print(h, T[h], s)
print("unmatched", [T[h] for h in T if h not in hits])
json.dump(hits, open("../out/k38_topic_names.json", "w"), indent=1)
