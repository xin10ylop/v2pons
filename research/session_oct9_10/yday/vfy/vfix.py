"""Write follow_verified.json: follow.json with the one record-level correction found (trade 8's live field omitted the two
approval transactions our wallet sent for the router route) and the verification summary in meta."""
import json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
SRC = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/yday/follow.json"
DST = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/yday/follow_verified.json"
d = json.load(open(SRC))
appr = ["0x4160327ee64f210a6757f4b71a87141a0d12af4df800e091bb93a8080f68df8a", "0xf44cb99fbdda4aae7dd7efa9c9a19e736a2a234d582d75c715d3df5292f92576"]
rs = batch([("eth_getTransactionReceipt", [h]) for h in appr])
r8 = next(r for r in d["launches"] if r["block"] == 83386507)
lv = r8["live"]
for h, r in zip(appr, rs):
    g = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16)
    lv["legs"].append({"tx": h, "block": int(r["blockNumber"], 16), "index": int(r["transactionIndex"], 16), "status": r["status"], "gas_used": int(r["gasUsed"], 16),
                       "gas_eth": g / 1e18, "to": r["to"], "what": "approval (router route), added by the verifier"})
old = (lv["gas_eth"], lv["pnl_eth"], lv["ret_net"])
lv["gas_eth"] = sum(x["gas_eth"] for x in lv["legs"])
lv["pnl_eth"] = lv["eth_out"] - lv["eth_in"] - lv["gas_eth"]
lv["ret_net"] = lv["pnl_eth"] / lv["eth_in"]
lv["verifier_note"] = (f"corrected: the two approvals (ERC20 approve to Permit2 at +46, Permit2 approve at +47; 46,189 + 47,818 gas) were missing; "
                       f"gas {old[0]:.4e} -> {lv['gas_eth']:.4e} ETH, pnl {old[1]:.4e} -> {lv['pnl_eth']:.4e} ETH, ret_net {old[2]:+.4f} -> {lv['ret_net']:+.4f}. "
                       "The unsold 10% (3.48e22 tokens) is still in the wallet; the pool was pulled at +9901, so it is counted as zero.")
d["meta"]["verification"] = {
    "by": "adversarial verifier, independent code yday/vfy/{vfetch,vgas,vprice,vcrowd,vpfee,vcopies,vcross}.py (no follow.py / cache_follow.pkl)",
    "repriced": "all 51 launches, 46 traded x 3 stakes x 4 variants = 552 results: ret within 5.0e-7 (the pricer's 6-decimal rounding), exits, buy/send/land blocks, pull, fire, trigger, close_block identical",
    "record_corrections": ["83386507 (14:32:16, trade 8) live: approval gas added, ret_net -0.0973 -> " + f"{lv['ret_net']:+.4f}"],
    "report_corrections": [
        "'the 27 launches 09:45-11:14 average about +2.2% (land1_fast)': 09:45-11:14 holds 25 launches averaging +1.83%; 27 / +2.2% is 09:45-12:27 (adds 12:07 and 12:26)",
        "'our fill comes to 0.996 of minOut on one of them': three of the four land2 reverts are within 0.4% of minOut (0.9964, 0.9971, 0.9982; the fourth 0.960), and three land2 fills pass by 0.24-0.49% (1.0024, 1.0026, 1.0049): land2 on 6 launches flips on intra-block order",
        "'the Swap fee field rises on 8 pools from +118': a ProtocolFeeUpdated event exists for all 51 pools, the earliest at +115 (10:17:37); every one is after its pool's trade window, so the conclusion stands",
        "'At 0.004 they total +0.00168 ETH; at 0.012, +0.00500 ETH': true for land1_slow/land2_*; land1_fast is +0.0000504 and +0.000176 ETH",
    ],
    "checked_ok": [
        "summary table (12 rows: mean, median, worst, wins, total, exits) recomputed from follow.json: all match",
        "cap-3 day (05:59, 06:05, 09:45) recomputed: +6.4e-6 ETH land1_fast / +4.974e-4 ETH other variants at 0.0012; +5.04e-5 / +1.6795e-3 at 0.004; +1.757e-4 / +4.997e-3 at 0.012",
        "pool list complete: rebuilt from all Oct 8 Initialize events: 51 orig, 49 copy, first orig 05:59, first copy 14:59; no operator launch in the last 2000 blocks of Oct 7",
        "all 49 copies' launchers carry code hash 2793923d... (seat); none would take the follow entry",
        "launch and crowd txs are type 0x0/0x2 (parse_tx sees them); no feed tx carries a second armed token (on_buy's break)",
        "feed trigger = chain's first >= 0.0002 ETH swap on all 46; trigger tx last of its block (minOut identical either way); feed copy vs chain sqrtP within 3.4e-7",
        "no range crossed, no ModifyLiquidity inside any window; protocol fee updates all after the windows",
        "crowd buys behind ours: 484 checked against their own amountOutMinimum with our buy ahead: only the 0.0001 ETH dust buy at 06:05 reverts, at 0.012",
        "gas: buy 103,861, sell 103,894, pulled-pool sell 135,200 (medians of our Oct 8 relay receipts); effectiveGasPrice == block baseFee on all 18 relay receipts",
        "blocks ran 9-10 per second around every trigger: the 0.5 s sell fallback (about T+5) comes after the B+2 deadline (T+3 / T+4)",
        "skips: 11:46, 11:51 fee 10000 > 9999; 12:28, 12:43 no ETH buy carrying the token at all in +0..+160; 13:21 first real buy +208 > 150",
    ],
}
json.dump(d, open(DST, "w"), indent=1, default=str)
print("wrote", DST, "trade 8 ret_net", old[2], "->", lv["ret_net"])
