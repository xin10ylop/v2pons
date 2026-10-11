# What it costs our v3.0 front if the outside fronter's sell lands ahead of ours at bot+1, at the launch state of v3.0
# (sqrtP and L from s1_basics), our 0.0058 buy first, then the fronter's buy, then the bot's buy (median and extremes), then the two sells.
import sys, json
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
SP = 679394651928963067279918579724198; L = 25725498245903809899643; FEE = 10000; GAS = 4_200_000_000_000
def net(x): return x - (x * FEE + 999_999) // 1_000_000
out = {}
for f_eth in (0.00099, 0.00495):
    for bot_eth in (0.0495, 0.124, 0.236):
        X = int(0.0058e18); F = int(f_eth * 1e18); B = int(bot_eth * 1e18)
        sp = SP
        ours = v4math.buy_out_int(sp, L, X, FEE); sp = v4math.sqrt_after_buy(sp, L, net(X))
        fr = v4math.buy_out_int(sp, L, F, FEE); sp = v4math.sqrt_after_buy(sp, L, net(F))
        sp = v4math.sqrt_after_buy(sp, L, net(B))
        first = (v4math.sell_out_int(int(sp), L, ours, FEE) - X - GAS) / X
        # fronter sells first: move price down by its token sale (sqrtP after a token-in sell: 1/sqrtP adds tokens/L in Q96 units... use the
        # ETH it receives to back out the new price: selling t tokens lowers sqrtP by delta(sqrtP) = eth_out_gross / L in Q96)
        frn = fr - (fr * FEE + 999_999) // 1_000_000
        sp2 = int(sp) + (frn * (1 << 96)) // L                 # a sell (token in) raises sqrtP: s' = s + t/L
        second = (v4math.sell_out_int(int(sp2), L, ours, FEE) - X - GAS) / X
        out[f"fronter {f_eth} bot {bot_eth}"] = {"ours_first%": round(100 * first, 2), "ours_after_fronter_sell%": round(100 * second, 2), "cost_points": round(100 * (first - second), 2)}
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/merge/order_cost.json", "w"), indent=1)
