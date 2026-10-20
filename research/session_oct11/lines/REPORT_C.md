# Analyst C: Uniswap V2 and V3 lines, Oct 11

Verdict: one V2/V3 line holds up when every launch is traded: the V3 crowd line, about $185/day at $15, positive on all 7 days. Every other
line that looks big in the plain replay is reversed by the operator's reaction to an outside buy or by a behaviour change in the last 24 h.
Rules: buy at +2; sell k blocks after the first real buy that lands after ours, or at a cap.

## Candidates
1. V3 crowd line (tok:d4e7eae4 1,013 + 1d7cd90a 22 + cb79985d 11): 1,046 launches, 149/day (153/155/167/149/142/134/146). V3 PositionManager
   0x73991a25 multicall ac9650d8, 836 B, value 0, fee 100 / ts 1, WETH quote, fresh wallets; the multicall creates and initialises the pool,
   mints a token-only range from the minimum tick to the launch tick (1e9 tokens), refunds ETH; one constant one-sided range until the burn;
   the simulator matches real swaps to ~1e-12. The buy we sell into: a crowd of 282 wallets reused across pools through bot contracts
   0x80114879/0xd26c8cfc/0xa28f468c/0xaf9d6fa0; first real buy at +47/+86/+264, median 0.05 ETH, missing in 13%; the wave in the next 20
   blocks: 5 buys, 0.34 ETH, price +17.4% (p10 +2.4%, p90 +58.8%). Pulls: 79% of pools by the launch wallet at +128/+301/+1216, none before
   the first real buy; no-crowd launches pulled from +83. No reaction to outside buys (12% vs 17%). Best rule: buy at +2, sell 20 blocks after
   the first real buy or at +80: n 1046, mean +8.5%, median +0.2%, win 0.88, worst -0.03%, 0 pulled, $1.24/trade, $185/day; per day
   +8.9/+15.9/+6.2/+10.3/+5.7/+6.3/+5.5%; the last 24 h $116; the top 10% of trades bring 71% of the PnL. Cap +60: $95/day; cap +100: $224/day
   with 1.8% pulled. Engine: new trading path. Top risk: the +80 exit is 3 blocks before the earliest no-crowd pull; the crowd's min-out is
   unreadable from the cached calldata.
2. lc:0a493d1a|13ead562 (V3, 70/day, bursty; watch only): the launch wallet mints at +7 then buys exactly 0.05 ETH itself at +22/+28/+35 through
   SwapRouter02 0xcaf681a6 with minOut 0 (431/431); buy at the mint +2, sell after its buy, cap 60: +66% mean, 95% win, 2.1% pulled, $678/day,
   but broken in the last 24 h (-12.7%): in 46 of the last 58 launches the operator's buy fell to 0.001 ETH.
3. tok:70adce63 (V2, 169/day): router 0x89e5db8b addLiquidityETH with 30-50 ETH; seven operator wallets buy 0.5 ETH at +202 with a 1% min-out;
   buy +2, sell after their buy: +1.9% mean, 0.84 win, $44/day; but the operator pulls 151-189 blocks after an outside buy (47 of 61 pools vs
   14 of 1,119): if that clock starts at our buy the mean is -97%.

## Rejected
tok:0f34e3b5 (86/day): the fleet sets min-out = quote - 0.05% on a 1-2 block stale quote (53 of 53), so any buy ahead reverts its first buy;
pair creation and the liquidity add are one tx; after a stranger buys the pool is pulled 77-95 blocks later in 12 of 13 pools; a reaction-safe
follow makes $37/day and the line was absent 48 h. The fleet: 5,048 single-use wallets funded by one hot wallet 0x4a6dbb33...fe70; buys 0.04
ETH median, 24 per pool ~105 blocks apart, x3.8 by +3000, 27% pulled at +269. lc:bd55ea26|f305d719: the union of the two V2 families above.
lc:89885b75|d27d1e00, 97c7ba1b, 2be340ff: 137 of 248 launches carry the launcher's own buy at +0, front ~0%. lc:cecb292d|8cb5772c: a real buy
in 12 of 2,003. fa4982d5 launchpad pairs ~$4/day. b09ef517|e9ae5c53 down to 1 launch in 24 h. c40bd4ef a one-day burst. ad9da489, 516ca2d6
negative and gone. 0a600ad0 liquidity and first buy in one tx. 884da06b Oct 7-9 only.

## Limits
Replays cannot show how others respond to our buy; reverted transactions are not in the data; V2 reserves rebuilt from events are exact for
these families but off 10-12% on v2b launchpad pairs; landing at L+2 was measured on v4 only; fleet funding from the 2.6% of blocks cached;
no visible token tax, outsiders' sells returned ETH. Scripts s01-s24, replay.py, fams.py and outputs in analysis/C/.
