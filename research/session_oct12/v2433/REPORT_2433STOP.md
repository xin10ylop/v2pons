# REPORT_2433STOP: what happened to the 2.433 line (Oct 12, 2026)

Verdict (two analysts, the skeptic did not refute): the operator changed nothing and shut the line down after its 02:06:02 UTC launch (pull 02:12:21); its wallets were swept into one wallet within 70 s, and at 13:08-13:09 UTC that wallet bridged 9.3 ETH to Ethereum mainnet. No successor shape exists on Robinhood Chain; the bot router now buys only in the 3.0 and 5.0 lines. The engine needs no change: the same value would be traded again automatically; a new value would show as a new shape (>= 10 launches in 3 h) in the routine watch.

## Analyst: launches

### Conclusion

The operator changed nothing in the 2.433 line. They stopped it after an ordinary cycle, and nothing replaced it. I checked all 3,954 PoolManager Initialize events from Oct 11 18:00 UTC to Oct 12 14:30 UTC (blocks 86026586..86745109), across every currency pair and every sender and target.

- **The 2.433 line ran unchanged to the end.** It made 91 launches at a steady 9-13 per hour (one about every 6 minutes). All 91 carry the identical fingerprint: same value, calldata length, fee, tick spacing, price, liquidity, range, gas limit and token code. The calldata of each launch differs only in the token address, the recipient (its own sender) and the deadline.
- **The last launch** was at 02:06:02 UTC Oct 12, block 86310320. That pool ran its normal cycle. The decoy-router wallet bought at +2, our relay at +2 and the bot at +10. The bot then bought 40 times (5.11 ETH). The launch wallet pulled the pool at +3,689 (02:12:21) through the bot router. The next launch would normally have come about then, and it never did. As of 14:30 there has been no 2.433 launch for 12.4 hours.
- **The 3.0 and 5.0 lines kept going.** The bot router still buys, and only in those two lines, at the same rate and with the same ETH per hour as before the stop. The roughly 80 ETH per hour it spent on 2.433 was not moved anywhere: its total buying fell from about 400 to about 330 ETH per hour.
- **No successor exists.** I checked every trait, and no cluster that started or grew around 02:06 has any 2.433 trait:
  - no other value of exactly 2.4333285, and no ETH launch within 10% of it after 23:18 Oct 11;
  - nobody else uses that price or liquidity, or fee 5000/ts 100;
  - no new launch uses the 1,526-byte 2.433 token code;
  - no other contract has the bot router's code;
  - no Uniswap V3 launch looks like it;
  - the 2.433 wallets did not move into the 3.0 or 5.0 lines.
- **The 2.433 wallets are empty.** All 91 launch wallets and the 2.433 buyer wallets that sent their own buys (122 of 342) now hold exactly 0 ETH.

The chain does not show why the line stopped. It shows a clean wind-down, not a new fingerprint the engine fails to match, so the engine needs no change to see it. If the line comes back with the same value, the current exact-value match catches it. If it comes back with a new value, the strongest tell will be its token: a 1,526-byte token (code hash 63ad5291cdef…, address ending in 777), deployed through the bot router 0x1cbaf24d with selector 0x7422a284 and minted to it.

Three side notes:
- **Our relay's last trade was later than the box says.** On chain it traded the final 02:06:02 pool: buy at 02:06:02, sell at 02:06:03, +9.4%. The box says its last trade was 02:00:33. The relay has made no swaps of any kind since.
- **The hourly watch script prints wrong fee and tick spacing.** research/session_oct11/recent_launches.py reads `fee = W(d, 2); ts = W(d, 3)`, which are the hooks and sqrtPriceX96 words; the fee is word 0 and the tick spacing word 1. The watch groups by value, so its "no 2.433 launch" finding still holds.
- **I did not analyse the v3crowd output you pasted.**

### What changed

Every 2.433 field was the same from the first launch in the window (18:03 Oct 11) to the last (02:06:02 Oct 12, block 86310320). The only change is that it stopped. The last pull was 02:12:21 (block 86314009); there have been no launches since.

- **Value:** 2433328500000000000 wei on all 91 launches, unchanged.
- **Calldata:** 1,444 B, multicall 0xac9650d8, to the PositionManager 0x58daec31 on all 91, unchanged. Byte by byte, only the token, the recipient (= the sender) and the deadline differ between launches.
- **Fee and tick spacing:** 5000/100 on all 91 (the switch from 2500/50 was Oct 11 15:32, before this window).
- **Hooks:** 0.
- **sqrtPriceX96 and liquidity:** 1604517591721945638372359205383840 (tick 198329) and 49279426163460954002188, full range -887200..887200, on all 91. That is exactly 2.433329 ETH plus 998M tokens.
- **Gas:** limit 15,000,000; price about 0.024 gwei.
- **Sender wallets:** a different wallet on every launch. Each deploys its token through the bot router at nonce 8, launches at nonce 11 (one at 12) and pulls at nonce 13. All are now at nonce 15 (two at 16) with balance exactly 0.
- **Funders:** not traced. Native ETH transfers leave no logs.
- **Token deploy:** through the bot router 0x1cbaf24d, selector 0x7422a284. 1B tokens are minted to the router and fanned out in exactly 222 transfers on every token. Token code is 1,526 B with a single code hash on all 91, and every address ends in 777.
- **Bot router:** the same 0x1cbaf24d throughout. Its buys use 0xc1120e3d and swap through the Universal Router; its pulls use 0xa0f7978d. Per pool: first buy T at median +8..+9 (min +7), median 73-81 buys and 8.0-9.6 ETH in every 2-hour block. Per hour: 82, 89, 85, 79, 80, 80, 80 and 75 ETH, then 14 in the 02 hour and 0 after.
- **Buyer wallets:** the line's own set (342 buy recipients, 312 fan-out recipients), with only 1-2 shared with 3.0/5.0 before or after the stop.
- **Decoys:** the 0x65050a9b router at +1/+2 with about 0.005 ETH (wallet 0xc32ccde1, sells at +9), and 0xe71a69f4 dust at +3, in every late pool.
- **Timing:** about 11 launches per hour, median gap 6.0-6.2 minutes. The pull came at median +3,257..+3,396 blocks, which is just before the next launch.
- **Last two hours (00:06-02:06):** 22 launches with no drift. The only early pulls (+48, then a relaunch 22 s later; +792; and +140 at 00:00) also happened in earlier hours.
- **Our relay:** traded every one of those pools, buying at +2 and selling at +9..+12. Its stake was 0.007 ETH until 01:45:52 and 0.002 ETH from 01:46:14; that is our engine, not the operator.
- **Price and liquidity elsewhere:** no other launch in the window has this price or liquidity.

### New shape

none

### Evidence

**Last 2.433 launch**
- Tx 0x18cb2709602ac271f87a84fb7080cca37e0809d19a4c35018f7a6230ad001b11 at 02:06:02 UTC Oct 12, block 86310320.
- Sender 0x3fd5c7ca6a06b568b6ceccfea414a63a91acb2a7; token 0xb28f2d1f01b659bdffd762f4fac660dd25057777; pool 0x55a352811c40b46156201546cb5798e97d6cabb5166e8bcbec36924ad8dad995.
- Pull tx 0x501ab4dc593f47c73813bdfe7daa9f47cf68e3277d98be450cd817d054d093d at 02:12:21, sent by the launch wallet to the router with 0xa0f7978d.

**2.433 launches per hour, Oct 11 18h through Oct 12 02h:** 9, 12, 13, 12, 12, 9, 11, 11, 2, then 0 through 14h (s10).

**All clusters per hour (s10)**
- VB 3.0: 697 launches, about 20 per hour. They jump to 139 and 98 per hour at 08-09 UTC, with only about 5 bot buys per pool from 07 to 11 UTC, while the bot's total buys per hour stay flat. This is a change inside the 3.0 line, still 3 ETH with the 3.0 price, not 2.433.
- VB 5.0: 180 launches, 6-19 per hour.
- C-1: 166 launches.
- Operator A: 56 launches, none after 07:29.
- Everything else is unrelated.

**Bot router buys per hour (s07, s15)**
- Every token transfer into 0x1cbaf24d came from the PoolManager or a mint, so it trades only on v4. After 02:07 it buys only in 3.0 and 5.0.
- 3.0: about 1,450-1,800 buys and 228-279 ETH per hour, before and after the stop.
- 5.0: about 730-880 buys and 75-94 ETH per hour, before and after the stop.
- The 968 tokens minted to the router in the window launched as 3.0 (697), 5.0 (180) and 2.433 (91). There were none afterwards and no other cluster.

**Trait searches (s16-s20)**
- Value: 260 distinct values in the window. Exactly 2.4333285 appears only on the 91. Within 10%: operator A (10 launches, 2.2-2.65 ETH, the last at 23:18 Oct 11) and two hooked 0x82a55dde launches (2.3024 and 2.4024 ETH; tick spacing 1, concentrated ranges).
- Price and liquidity within 3%:
  - a single-sided cluster (30 launches 18:25 Oct 11 to 13:52 Oct 12; fee 2500/ts 25; range -160100..198050; sqrtP 1.5822e33, L 5.0074e22; position NFT always to 0x23f82095). It used a CREATE launch at 3.4 ETH, then the 0x0000ffffbe router from 02:05:11;
  - 0xd0fd42bd (6 launches);
  - operator A.

  These are the common "1B tokens at about 2.5 ETH FDV" pricing. The bot router never bought in them and their token code differs.
- Calldata of 1,444 B: 1,185 launches in 104 clusters. It is simply the standard PositionManager length for an ETH pair.
- Fee 5000/ts 100 or 2500/50: only 2.433 in the whole window.
- 2.433 token code (1,526 B, one hash): no new launch uses it. Six non-ETH re-pairings of old 2.433 tokens by another bot ended at 00:08.
- Router code: the bot router's code hash is bd31d4da7db89e01a9bb257fb9840da42b80df746dd53b9e7bf6a245d2cf8968 (20,443 B). The first-mint recipients of all 1,915 newly minted ETH-pair tokens include no other contract with it.
- Uniswap V3: 202 PoolCreated events, none at or near 2.4333.
- Wallets: the 2.433 wallets do not appear in 3.0/5.0 after the stop (s12).

**Limits**
- A reverted launch attempt emits no logs and would not show.
- Funding of the launch wallets by native ETH is not traceable without a trace API.

**Cost:** about 1,500 paced requests, public RPC only.

### Files

All under /home/user/v2pons/research/session_oct12/v2433/fp/. Scripts are s01..s23 .py plus common.py (pacing via c1/rpc.py) and clusters.py. Raw caches are *_cache.jsonl (ignored by git); I committed nothing.

Key outputs:
- /home/user/v2pons/research/session_oct12/v2433/fp/s10_hourly.out — hourly counts per fingerprint cluster
- /home/user/v2pons/research/session_oct12/v2433/fp/s07_bot_by_cluster.out — the bot router's buys, mints and pulls per hour per cluster
- /home/user/v2pons/research/session_oct12/v2433/fp/s15_bot_eth.out — the bot's ETH per hour per line
- /home/user/v2pons/research/session_oct12/v2433/fp/s09_last_table.out — the fate of the last 24 2.433 pools
- /home/user/v2pons/research/session_oct12/v2433/fp/s22_lifecycle.out — 2.433 lifecycle by 2-hour block, and the last launch
- /home/user/v2pons/research/session_oct12/v2433/fp/s23_calldata.out — byte-level calldata drift
- /home/user/v2pons/research/session_oct12/v2433/fp/s16_traits.out — trait matches
- /home/user/v2pons/research/session_oct12/v2433/fp/s17_codes.out — token templates
- /home/user/v2pons/research/session_oct12/v2433/fp/s18_mints.out and /home/user/v2pons/research/session_oct12/v2433/fp/s19_creators.out — router-clone search
- /home/user/v2pons/research/session_oct12/v2433/fp/s20_v3.out — V3 pool creations
- /home/user/v2pons/research/session_oct12/v2433/fp/s12_wallet_sets.out — wallet overlap between lines
- /home/user/v2pons/research/session_oct12/v2433/fp/s13_idle.out — wallets idle and empty
- /home/user/v2pons/research/session_oct12/v2433/fp/s21_relay.out — our relay's last trades

The launch table itself is /home/user/v2pons/research/session_oct12/v2433/fp/s03_launches_cache.jsonl: one row per Initialize, with block, time, sender, to, selector, value, calldata length, currencies, fee, tick spacing, hooks, sqrtP, minted liquidity and range.

Separately, the watch-script bug is in /home/user/v2pons/research/session_oct11/recent_launches.py (fee and tick spacing read from the wrong words).

## Analyst: wallets

### Conclusion

The operator deliberately shut the v2.433 line down between 02:06 and 02:13 UTC on Oct 12, and later took its money off Robinhood Chain. It did not move the line to another value, venue, router or wallet scheme on this chain, and it did not slow down first.

Sequence of the stop:
- **Last launch.** Block 86310320 at 02:06:02, sent by wallet 0x3fd5c7ca. The fingerprint was unchanged.
- **Last pull and sweep.** The pool was pulled at +3,689 blocks (02:12:21). At 02:12:26 the wallet swept 3.904 ETH to 0x6c3bd8f6. That wallet had been prepared as the next launch wallet (already at nonce 8, after the same 8 setup transactions as every launch wallet) but it never launched.
- **Consolidation.** Over the next 70 seconds, the line's 31 dedicated buyer wallets emptied into 0x6c3bd8f6 (4.596 ETH), along with dust from 34 retired launch wallets. The total collected was 8.49998 ETH.
- **Withdrawal.** 0x6c3bd8f6 sat untouched for 11 hours. At 13:05:52 it received a further 0.7999 ETH. At 13:08:45 and 13:09:46 it sent 0.1 ETH (a test) and then 9.199 ETH into a cross-chain intent deposit contract. Relayers bridged both amounts to Ethereum mainnet through the Across-style spoke pool.

Nothing of the line is left on chain:
- All 150 of the last launch wallets are empty (1.4e-5 ETH in total) and at their final nonces.
- The 31 buyer wallets hold 0 ETH and have not sent a transaction since 02:12.
- The volume-bot router carries only the 3.0 and 5.0 lines now.
- No launch with the 2.433 value, price or fee/tick spacing has appeared up to block 86791292 (15:48:56 UTC).

The decoys and fronters stopped in the last 2.433 pool, at 02:06:03 to 02:06:05.

Best reading: the line was stopped and its working capital (about 9.3 ETH) withdrawn. Nothing on this chain shows it being replaced, and I could not follow the money past the bridge. I can't tell whether it restarted on another chain; only the Robinhood RPC was used.

One discrepancy with the brief: our relay also traded the very last pool. It bought 0.002 ETH at +2 (02:06:02) and sold at +12 (02:06:03) for 0.0021874 ETH. That is later than the 02:00:33 noted as the box's last trade.

### What changed

Values below are old -> new, with the first block or time of the change.

- **Launch value, calldata, PositionManager, price, liquidity, hooks:** no change right up to the end. All 150 of the last launches (Oct 11 15:24:52 to Oct 12 02:06:02) had:
  - value exactly 2433328500000000000 wei, sent to PositionManager 0x58daec31 as a 1,444-byte multicall;
  - sqrtPriceX96 1604517591721945638372359205383840;
  - minted liquidity 49279426163460954002188;
  - hooks 0;
  - legacy-style gas at tip = max fee of about 0.024 gwei.
  - After block 86310320 there is no launch at all: 0 Initialize events with that price or with fee 2500/50 or 5000/100 up to block 86791292 (15:48:56), and 0 transactions with that value.
- **Fee and tick spacing:** 2500/50 -> 5000/100 at 15:33:56 Oct 11 (block 85940923, already known). In the last 150 launches: 21 at 2500/50, then 129 at 5000/100.
- **Pull timing (within the fee-5000 era, not new today):** most pools (103 of 150) were pulled on what looks like a timer, +3,138/+3,415/+3,654 blocks (p10/p50/p90), about 5.5-6 minutes. The other 47 were pulled early, between +12 and +792. The line runs strictly one pool at a time: each next launch comes 156/173/195 blocks (p10/p50/p90) after the previous pull, with no overlap. That gives about 10-13 launches an hour. There was no slowdown before the stop: 11 launches in the 00h hour, 11 in the 01h hour, 2 in 02:00-02:06.
- **Sender wallets:** the same scheme until the end. Each launch uses a new wallet that launches at nonce 11 (8 earlier setup transactions, origin not traced). Each wallet then sends, in order:
  1. 7422a284 to the bot router (token deploy, about 1.7 ETH on average);
  2. a token approve;
  3. a Permit2 approve;
  4. the launch;
  5. an approve of the position NFT to the router;
  6. the pull (a0f7978d through the router);
  7. a sweep of its whole balance to the next wallet.
  - The prepared next wallet, 0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d, never launched. Its nonces 8 and 9 were the two bridge deposits at 13:08:45 and 13:09:46.
- **Funders:** a single closed chain.
  - 148 of 150 launch wallets were funded by the previous launch wallet's sweep after the pull (2.68/4.15/4.85 ETH, p10/p50/p90, about 115-124 blocks before the launch). The other two are the window's first launch, funded by 0x74447adf (the wallet before it), and 0xfdef3270's second launch from the same wallet.
  - 31 recurring buyer wallets (nonces 37,991-41,202) topped up the new wallet in the same minute: in 111 cycles, 894 transfers, 43.5 ETH in total.
  - None of these funders has sent anything since 02:13. The final destination was 0x6c3bd8f6, and from there the money went to the bridge (see the evidence field).
- **Bot router 0x1cbaf24d:** unchanged (same 20,443-byte code, hash bd31d4da...). The 3.0 and 5.0 launch wallets still call it for 7422a284 deploys and pulls.
  - I sampled it every hour (1,000 blocks, about 100 s, per hour). That gives about 2,400-4,500 router transactions an hour, from Oct 11 18:00 to Oct 12 15:00.
  - Buys at Oct 11 18:00-02:00 were v3.0 about 55-65, v5.0 about 30, plus v2.433 in alternate samples. From 03:00 they are v3.0 and v5.0 only, at the same levels.
  - The last v2.433 buy seen in the samples was at 02:01:41.
  - 0 calls with its selectors went to any other address, and none of the 103 contracts created in the sampled blocks has its code: no clone.
- **Buyer wallets:** the 31 v2.433 buyers bought only in v2.433 pools (208 sampled buys, 0 elsewhere). All of them swept into 0x6c3bd8f6 at 02:12:26-02:12:37 and have been silent since.
  - The v3.0 and v5.0 lines use separate buyer sets: 3.0 buyers at nonces 52k-68k, 5.0 buyers at 38k-41k.
  - Router callers: 259 seen before 02:00, 227 after 03:00; 209 in both, 18 new.
- **Decoys and fronters:**
  - The fresh-wallet decoy series (about 0.00495 ETH at +2 via 0x65050a9b, one fresh wallet per 2.433 pool) made 169 buys between 15:11 Oct 11 and 02:06:03 Oct 12, the last in the last pool. It has made none in any of the bot's lines since.
  - 0x8cf143dd made 116 tiny buys via 0x65050a9b in 2.433 pools, the last at 02:06:05. It then made 45 buys in v3.0 via 0xfd1b271f (04:48-06:18), and has been idle since (nonce 3,108 -> 3,111).
  - 0xb8c879dc made 136 buys via 0xfd1b271f in 2.433 pools, the last at 02:06:05. It then made 6 buys in v3.0 (04:48) and 3 in v5.0 (05:42-06:08). It is still active elsewhere: 474 transactions since 06:08, through 0x65050a9b on token 0x52e3bf36, with no v4 Swap log (another venue).
  - 0x7ae81404 is active through the Universal Router (1,124-byte calldata, 2e-5 ETH buys in older pools).
  - 0x65050a9b is not a wallet. It is a shared 752-byte router, still used chain-wide (26,297 swaps since Oct 11 12:00, active at 14:47).
  - The collectors 0x544ef435, 0xe322fc6d and 0x488faf52 and both router admins show nothing new in the last 5,000 blocks.
- **Hub flows:** 0x6c3bd8f6 is the only hub of the line. Its incoming and outgoing flows are listed in full in the evidence field.

### New shape

none

### Evidence

**Last cycle and stop:**
- Launch tx 0x18cb2709602ac271f87a84fb7080cca37e0809d19a4c35018f7a6230ad001b11, block 86310320, 02:06:02, from 0x3fd5c7ca6a06b568b6ceccfea414a63a91acb2a7 (nonce 11).
- Its 7422a284 call: 0xa1c40b8e..., block 86310308.
- Pull: 0x501ab4dcc593f47c73813bdfe7daa9f47cf68e3277d98be450cd817d054d093d, block 86314009, 02:12:21.
- Sweep: 0x9a33f2d4b668784b5e7de2a411fcf59729cd881bc839e13fb397171a5053326f, block 86314055, 3.9041 ETH to 0x6c3bd8f6.

**Inflows to 0x6c3bd8f6 (w05_hub_inflows.out):** 74 transfers between 02:12:26 and 02:13:35, 8.499981 ETH in total:
- 1 launch-wallet sweep;
- 39 transfers from the 31 buyer wallets (4.5957 ETH);
- 34 dust sweeps (0.00017 ETH), 23 of them from launch wallets listed in REPORT_X's Oct 10-11 data.

A forward full-block scan from 02:19 to 03:19 found nothing more. The only later inflow is 0xe4f1b38affb3fdc0e0ed87045f867f03e00191f339d0536a6d4b79e267d06b88: block 86695397, 13:05:52, 0.7999 ETH from 0x39525d91ffdcc126f052eefed6735fda72ad1dee. That wallet holds 119.4 ETH at nonce 3,445, receives from nonce-0 wallets and pays out small amounts. It looks like an exchange or custodian; 0.7999 = 0.8 minus a 0.0001 fee.

**Outflows from 0x6c3bd8f6:**
- 0x0bad72bd9db03b99a0563d8daac9914ee7d04a9df82c2fb9ef54c9e64d5541b3: block 86697087, 13:08:45, nonce 8, 0.1 ETH to 0x794dbdbdbfd3f8a3b887f4513bf5ff29edd04a94 (selector 1e04ce08).
- 0x9b57f4e6d10fa22ca39d066d5bf1113f94dfc938411459b3a34eefb6ac5247f3: block 86697687, 13:09:46, nonce 9, 9.199 ETH, same contract.
- Each was relayed within 2 seconds by 0x394311a6 and 0x07ae8551 through 0x998d7c17 (selector e3a64e34): tx 0x8d18b0ee04940255815ec638c86e90570bb8dfd6fb3a360e677a62fa86b8ddcf (block 86697103) and tx 0xc04476ce4a9676852106a1e35ad37b2be0aaa9425a28af70a5d45cebb922f5d3 (block 86697705).
- Those emitted FundsDeposited events on the spoke pool 0xd29c85f15df544ba632c9e25829fd29d767d7978:
  - destination chain 1 (Ethereum), depositor 0x6c3bd8f6;
  - input token is this chain's WETH 0x0bd7d308, output token is mainnet WETH 0xc02aaa39;
  - output 0.09992 + 9.19843 ETH;
  - recipient 0x4216e5ae6021c523aae05b6ac6824f3c096cf905.
  - That recipient took deposits from about 170 depositors on this pool since Oct 10, so it is a shared receiver and the money cannot be followed further.
- Balance check: 8.49998 + 0.7999 - 9.299 - 0.00088 (left) = 2.4e-7 ETH of gas. Its current nonce of 10 is consistent with this.

**Chain of the last 150 launches (w12_chain_table.out):**
- 148 funded by the previous launch wallet.
- 149 sweeps went to the next launch wallet; the last went to 0x6c3bd8f6.
- 31 buyer wallets made 894 top-up transfers, 43.46 ETH.

**State now (w15, w05_buyers_now):** the 150 launch wallets hold 1.4e-5 ETH in total (nonces 15 x144, 16 x4, 22 x2). The 31 buyers each hold 0, with nonce equal to their 02:12 sweep nonce + 1.

**3.0 and 5.0 launch wallets checked on recent launches:**
- 3.0, fresh-wallet chain: funded by the previous wallet (sender nonce 6, 3.66 ETH) plus 3.0 buyers at nonces 52-53k.
- 3.0, high-nonce wallets: funded by a sender at nonce 278 (6.76 ETH) plus buyers at 56-68k.
- 5.0: funded by a sender at nonce 244 (5.9 ETH) plus buyers at 38-41k.
- None of these senders is a 2.433 wallet, and they all still call 0x1cbaf24d.

**Our relay:** 25 swaps since block 86280000. The last pair was block 86310322 (buy 0.002 ETH at +2) and block 86310332 (sell 0.0021874 ETH at +12) in the last pool, 02:06:02-03.

**Other launches after the stop (w02):** POSM launches after 02:06 are 3.0 (spike of 139 and 98 an hour at 08:00-09:00), 5.0, 2276-byte value-0, and small lines (4e-05, 0.0012177, 4.0, 9.333). There is no new value.

**RPC use:** about 5,500 POSTs (119,888 items) to the public RPC only, all read methods.

### Files

All in /home/user/v2pons/research/session_oct12/v2433/wallets/. No .md report was written; the findings are in this answer. Raw caches are in *_cache.jsonl files (ignored by git). Nothing was committed, and src/, deploy/, tests/ and docs/ were not touched.

Shared code:
- common.py
- rpc.py (paced, read-only)

Launches:
- w01_inits.py: every Initialize since Oct 11 12:00
- w02_launch_txs.py: launch transactions for ETH-quoted Initializes
- w03_router.py: an attempt to count the router's swaps from Swap logs. It found 0, because the bot's swaps show the Universal Router as sender. w03_meta.json has the router's code hash.

Wallet traces:
- w04_life.py and w04_life_last_wallet.out: the last launch wallet's whole life
- w05_follow.py and w05_hub_inflows.out: 0x6c3bd8f6's 74 inflows at 02:12-02:13
- w05_buyers_now.json: the 31 buyer wallets' state now

Funding chain:
- w06_chain.py, w06_chain.json, w06_chain.out: full blocks around the last 150 launches and their pulls
- w12_chain_table.py, w12_chain_table.out, w12_chain_rows.json: who funded each wallet and where each sweep went
- w15_launchw_now.json: the 150 launch wallets' state now

Router:
- w07_router_sample.py, w07_sample.jsonl, w07_router_sample.out: hourly 1,000-block samples
- w14_router_table.py, w14_router_table.out, w14_creations.json: per-hour table, callers, clone check
- w18_creations.py, w18_creations.out: code hashes of contracts created in the samples

Decoys and fronters:
- w08_decoys.py: swaps through the two decoy routers
- w09_decoy_table.py, w09_decoy_table.out: per hour and per line
- w10_decoy_wallets.py, w10_decoy_wallets.out: the wallets behind those buys
- w11_recent_txs.py: a wallet's latest transactions, found by binary search inside the node's state window

Hub and bridge:
- w13_scan.py, w13_hub_fwd.out, w13_hub_back.out, w13_hits.jsonl: lean full-block scans for the hub's transactions
- w16_bridge.json: the two decoded bridge deposits
- w19_bridge_scan.py, w19_bridge_scan.out: every bridge deposit on this chain since Oct 10, with the depositors and recipients

## Skeptic (refuted: False)

### Conclusion

The analysts' key claims hold. I re-derived them with my own code from raw chain data, using only the public RPC: 1,193 paced posts, read methods only. Nothing was committed.

**What happened to 2.433:** the operator changed nothing in the line. They stopped it after one ordinary cycle at about 02:12 UTC Oct 12, and nothing replaced it. The wallet scheme, liquidity, value, fee, price, calldata and router were all identical through the last launch. After the last pool was pulled, the money was collected into one wallet. At 13:08-13:09 that wallet bridged 9.299 ETH to Ethereum mainnet.

- **Last 2.433 launch:** 02:06:02 UTC Oct 12, block 86310320, tx 0x18cb2709…1b11, sender 0x3fd5c7ca, token 0xb28f2d1f…7777.
  - It used the old fingerprint exactly: value 2433328500000000000, sent to the PositionManager 0x58daec31, 1,444 B, multicall 0xac9650d8, fee 5000 / ts 100, hooks 0, the 2.433 sqrtP, the 2.433 liquidity, full range, gas limit 15,000,000, sender nonce 11.
  - The pool was pulled at block 86314009 (02:12:21). There is no 2.433 launch from then to block 86793063 (15:51:42), about 13.7 h.
- **No launch since carries the line:**
  - Since the stop, the bot router 0x1cbaf24d has received tokens only from the PoolManager or from mints, in 3.0 and 5.0 tokens only. The only exception is the final 2.433 token, up to its pull block.
  - Those 3.0 and 5.0 launches keep their own exact values: 3 ETH and 5 ETH, fee 10000 / ts 200, their own sqrtP.
  - In no pool after the stop does the bot's first buy come at +16 blocks or earlier. The 3.0 line still has the bot's first buy at +19..+64.
  - The only launches with a 15,000,000 gas limit after the stop are 3.0 (557) and 5.0 (130).
  - No launch after the stop has the 2.433 price, the 2.433 liquidity (checked across all 91,715 ModifyLiquidity events), fee 5000/ts 100 or 2500/50, or a 2.433-like value.
- **The new shape:** there is none, so there is nothing to attribute to the same operator.
  - The 31 bot-buyer wallets that bought in 2.433 never appear among 3.0/5.0 bot buyers, before or after the stop. That is from a random sample of 3,000 buys after the stop and 1,500 before it.
  - All 31 swept to 0x6c3bd8f6 at 02:12:26-02:13:35, and so did the last launch wallet. They now hold only dust, too little to pay for a single transfer.

**Minor errors in the analysts' evidence (none changes the conclusion):**
- The launches analyst's pull tx hash is missing a character. The correct hash is 0x501ab4dcc593f47c73813bdfe7daa9f47cf68e3277d98be450cd817d054d093d.
- The wallets analyst puts the fee 2500 → 5000 change at 15:33:56, block 85940923. The first fee-5000 launch was actually 15:32:30, block 85940074 (tx 0x78ab3ffd…), which is outside the question.
- "Exactly 0 ETH" is really dust:
  - the 31 buyers hold 2.75e-6 ETH in total (at most 9e-8 each);
  - the 68 launch wallets that pulled hold 6.0e-6;
  - the last launch wallet holds 9e-8.
- The watch-script fee/tick-spacing bug that the launches analyst reported has already been fixed in commit ba3d81a.

**Our relay:** it did trade the final pool, buying at 02:06:02 (block 86310322) and selling at 02:06:03 (block 86310332): 0.002 → 0.0021874 ETH, +9.4%. The box's "last trade 02:00:33" matches the previous pool, which sold at 02:00:29. So either the engine log is missing the 02:06 trade or the brief read it wrong. That is worth checking on the box.

**Separate from 2.433:** the 3.0 line itself changed. From about 07h, many more 3.0 pools were launched (139 and 98 in the 08 and 09 hours) with a median of only 6-7 bot buys each, while the bot's total 3.0 buys per hour stayed flat. Its bot timing is unchanged and it is not 2.433.

The v3crowd dry output you pasted was not part of this task and I did not analyse it.

### Measured

All outputs are in /home/user/v2pons/research/session_oct12/v2433/skeptic/.

**k01/k02 (k02_classify.out): every PoolManager Initialize in blocks 85800000..86793063 (Oct 11 11:31 to Oct 12 15:51), 6,609 launches, each with its transaction.**
- Exactly 287 launches have value 2433328500000000000. The same 287 have sqrtP 1604517591721945638372359205383840, and the same 287 have fee/ts 2500/50 or 5000/100.
- All 287 share to = 0x58daec31, selector 0xac9650d8, 1,444 B, hooks 0, gas limit 15,000,000.
- Sender nonce is 11 on 285 launches (one at 12, one at 18). Every token ends in 777.
- 2.433 launches per hour, Oct 11 18h to Oct 12 02h: 9, 12, 13, 12, 12, 9, 11, 11, 2. Then 0.
- Last launch: block 86310320, 02:06:02. 2,643 launches by others came after it.
- Fee change: last 2500 launch 15:30:56; first 5000 launch 15:32:30, block 85940074 (k12_feechange.out).

**k03/k04 (k04_botbuys.out): all 53,665 token Transfers into the bot router, blocks 86100000..86792929.**
- 52,739 came from the PoolManager and the rest were mints. None came from any other venue.
- Bot buys per hour in 2.433 tokens: 666-709 an hour from 20h to 01h, then 131 in the 02 hour (the final pool), then 0.
- 3.0 tokens: 1,354-1,825 an hour throughout. 5.0 tokens: 680-884 an hour throughout.
- The only buys after block 86310320 outside 3.0/5.0 are 41 in the final 2.433 token. The last of them is in block 86314009.
- Family variants: every 3.0 token is (3 ETH, 10000, 200); every 5.0 token is (5 ETH, 10000, 200).
- Tokens minted to the router after 02h are 3.0 and 5.0 only.

**k05 (k05_perpool.out): the bot's first buy per pool, in blocks after launch.**
- 2.433 before the stop: p10/p50/p90 +8/+9/+10.
- 3.0: +26/+41/+52 before the stop and +26/+41/+55 after. 5.0: +30/+42/+56 before and +32/+44/+56 after.
- Pools after the stop with a first bot buy at +16 or earlier: 0.

**k06 (k06_newclusters.out, k06b_traits.out): launches after the stop.**
- Gas limit 15,000,000: only 3.0 (557) and 5.0 (130).
- Exact 2.433 sqrtP, or fee/ts 5000/100 or 2500/50: 0.
- Value within 10%: 2 hooked launches, ts 1, 1,252 B (0x82a55dde-type).
- sqrtP within 3%: 24 launches of other shapes (fee 2500/ts 25 single-sided, 0xd0fd42bd fee 100/ts 1, and others). None has 15M gas, and the bot never bought in them.

**k07 (k07_liq.out): 91,715 ModifyLiquidity events, blocks 86308320..head.**
- A liquidity change of exactly ±49279426163460954002188 appears 3 times: the pull of the previous pool (block 86310124), the last mint (block 86310320) and its pull (block 86314009, tx 0x501ab4dcc593…).
- Nothing comes within 1% of that liquidity after the stop.

**k08 (k08_relay_code.out): our relay and the bot router.**
- Our relay's last swaps were in blocks 86310322 (−0.002 ETH) and 86310332 (+0.0021874 ETH) in the last 2.433 pool. It made no swaps after that.
- The bot router's code is 20,443 B with keccak bd31d4da7db89e01. Its code at old blocks cannot be read because the node no longer holds that state.

**k09 (k09_buyers.out): who calls the bot router in 2.433 pools.**
- 4,263 bot-router transactions in 2.433 pools since block 86100000: 4,195 buys (0xc1120e3d) and 68 pulls (0xa0f7978d), 484.15 ETH spent.
- The buys came from 31 bot-buyer wallets with nonces 37,992-41,203.
- None of the 31 appears among the 283 callers in 3,000 sampled 3.0/5.0 buys after the stop, nor among the 230 callers in 1,500 sampled buys before it.
- Balances now: 31 buyers 2.75e-6 ETH in total, 68 launch wallets that pulled 6.0e-6 ETH.

**k10/k11 (k10_hub.out, k11_winddown.out): full-block scan of 86313950..86315000.**
- 74 transfers into 0x6c3bd8f6 at 02:12:26-02:13:35, 8.499981 ETH in total: 2 from launch wallets that pulled (3.904118 ETH, one of them the last launch wallet's 3.904115 sweep), 39 from 31 of the 31 bot buyers (4.595695 ETH), and 33 other dust transfers.
- 13:05:52: 0x6c3bd8f6 received 0.7999 ETH from 0x39525d91 (nonce 3,438).
- 13:08:45 and 13:09:46: it sent 0.1 and 9.199 ETH (nonces 8 and 9) to 0x794dbdbd with selector 0x1e04ce08.
- These were filled in blocks 86697103 and 86697705. The spoke pool 0xd29c85f1 logged destination chain 1, depositor 0x6c3bd8f6, input token WETH 0x0bd7d308, output token mainnet WETH 0xc02aaa39.
- 0x6c3bd8f6 now holds 0.00088 ETH at nonce 10.

### New shape

none
