# REPORT_BNBFREEZE: the BNB line is a honeypot (Oct 14, 2026)

Verdict (two analysts, a skeptic who reproduced every load-bearing claim): the launcher 0xc9b7cc61's tokens (both templates the engine allowed, codehashes 0x5faca898... 2,995 B and 0x18449a16... 1,365 B) carry an operator address in storage slot 6; `_transfer` reverts with empty data whenever that operator's allowance to the sender is odd. The operator arms it with a look-alike `approve(victim, odd)` 4-67 blocks after a stranger's buy. In 3 days (554 launches) 135 of 135 strangers who bought before the dump and held were frozen; the operator's 120 crowd wallets never. No entry offset, method, wallet type or gas price escapes it; it never expires. Our first live trade (pool 0x2de2620b, bought at L+52, armed at L+70) is a permanent -100% ($5). The dry run's +35% assumed every buy can be sold; with the freeze every trade of the rule is -100%. The pre-buy check (one-transaction round trip from a fresh harness) cannot see a mark written after the buy. LESSON for every line: test that an outside buyer who HOLDS can still sell, on chain, before going live.

## Analyst: code

### finding

The token (0x950e6818...19, "HMM / Thinking Cat") is a REACTIVE, PER-ADDRESS honeypot, not a blacklist-at-launch. Our first live trade (25 BNB pool, FIRST buyer at L+52) is frozen because the launcher bakes an "operator" address into storage slot 6, and the token's _transfer reverts with EMPTY data whenever that operator has given the SENDER an ODD allowance. The operator (0xbd418ce6...) armed the trap AFTER our buy with a plain-looking approve(ourWallet, 2^256-1) to the token (tx 0xc3177267..., selector 0x095ea7b3, at L+70, 18 blocks after our buy). 2^256-1 is odd -> our wallet can never transfer. transferFrom by the router hits the same gate (from=victim) -> "TransferHelper: TRANSFER_FROM_FAILED". The 7 crowd holders are simply UNMARKED (allowance[op][x]=0, even) so they trade freely, which keeps the pool looking healthy. There was "no admin blacklist call" exactly because the mark is disguised as a normal approve. Proven by eth_call/eth_simulateV1 state overrides on the live chain: setting allowance[op][sender] odd freezes any address (incl. fresh and crowd), even lifts it; the balance value, block number and timestamp are all irrelevant. Both whitelisted templates carry the identical mechanism. This means the engine's own big/early buys are the prime target and the position is a permanent -100%.

### rule

slot 6 = operator address, written ONLY in the constructor (no runtime SSTORE targets literal slot 6; confirmed in both templates). In _transfer(from,to,amt) the gate is:  revert(0,0) [empty data]  iff  (X == 0) && ( allowance[slot6operator][from] & 1 == 1 ), i.e. the operator's allowance TO the sender is ODD. X is an exemption flag that is 0 for an ordinary holder transfer. The allowance is read at mapping slot 1: keccak(from . keccak(operator . 1)). Only bit 0 (parity) is tested. Exhaustively proven with overrides on crowd and fresh addresses: values 0,2,4,...,2^256-2 (even) PASS; 1,3,5,...,2^256-1 (odd) REVERT. Exact opcodes: 2995-byte template (codehash 0x5faca89801207abc...1356, control-flow-flattened with 8-byte magic-state dispatch) at state 0x5ca4955a -> 0x04ce DUP8; 0x04cf ISZERO; 0x04d0 DUP4; 0x04d1 AND; 0x04d2 ISZERO; 0x04d3 JUMPI 0x04f8; else 0x04f5 PUSH0 PUSH0 REVERT. 1365-byte template (codehash 0x18449a1624d9c527...487bc, clean Solidity) at 0x02b8 PUSH1 0x06 SLOAD ... 0x02d7 KECCAK256; 0x02d9 SLOAD; 0x02da DUP1; 0x02db DUP6; 0x02dc ISZERO; 0x02dd DUP2; 0x02de AND; 0x02df ISZERO; 0x02e0 JUMPI 0x02e7; else 0x02e4 PUSH0 DUP1 REVERT. Arming method: operator calls the token's standard approve(victim, oddValue); 2^256-1 is odd and masquerades as a routine "infinite approval". Disguise confirmed: the Approval event logged a DECOY amount 779315887607126688577176379609004218641311158219 while raw storage of allowance[op][us] = 0xffff...ff (MAX, odd). BASEFEE/NUMBER/COINBASE/SELFBALANCE and STATICCALLs to precompiles 0x02/0x04 along the path are decoys (always-true/no-op anti-analysis junk).

### expires

Never, automatically. The marker is plain mutable storage (allowance[operator][victim]) with NO block.number, timestamp, or decay input to the gate. Evidence: the freeze is time-independent across every override test; the only levers that change the outcome are the stored allowance parity and slot 6 itself (zeroing slot 6, or setting the operator-allowance to any even value, makes our transfer pass immediately in simulation). A far-future block/timestamp simulation does not lift it (no temporal term in the predicate). The ONLY way our tokens become transferable is the operator writing an even value (e.g. 0) to allowance[op][ourWallet] via another approve -- which an adversary will never do. Therefore our 25 BNB position is permanently non-transferable: a locked -100%. (Note the "sentinel" trap: because 2^256-1 is the standard infinite-approval value AND is odd, an operator can freeze and un-freeze by toggling between 2^256-1 (frozen) and 2^256-2 (free), both looking like near-infinite approvals.)

### safe_entry

NONE. No buy timing, method, or recipient grants immunity; the freeze targets the SENDER (`from`), independent of how the sender acquired tokens or where they send them. Evidence: (1) method-independent -- our fee-on-transfer buy (0xb6f9de95) vs the crowd's exact-in buy (0x7ff36ab5) is irrelevant; in simulation a fresh address that never bought is frozen purely by setting allowance[op][addr] odd, and unfrozen by making it even. (2) recipient-independent -- our plain transfer to 0x...dEaD and to the pair both revert, and the gate reads `from`, never `to`. (3) timing-independent -- no block/timestamp term. (4) The 7 crowd buyers and 6 crowd sellers were NOT "safely entered" -- they are merely not-yet-marked; the operator can mark any of them at any later block with one approve. The only addresses that stay transferable are those the operator chooses not to target, and the engine's profile (first in, largest stake) is exactly the profile that gets marked -- here within 18 blocks. There is no safe entry into this launcher family; only not-being-noticed, which the engine's size guarantees against.

### edge

The rule (buy at L+50, sell at L+260 on this launcher's PancakeSwap V2 launches) re-prices to deeply negative / untradeable once the restriction is applied. The downside is not a tax or slippage but a discretionary, operator-triggered -100%: any position can be made permanently unsellable after the buy, and the engine -- buying earliest with the largest stake -- is the deterministic target. On THIS launch the 25 BNB pool is frozen (-100% of stake) while the pre-buy honeypot check falsely returned a clean ~99.5% round trip. One marked launch at -100% erases a long run of the rule's small L+50->L+260 gains, and marking is at the adversary's will rather than probabilistic, so no position size or hold window makes the expected value positive. The measured "edge" of the rule under this restriction is negative and the strategy against this token family is a trap, not an edge.

### fix

1) Engine codehash list is inverted. src/bnb_live.py lines 65-66: BNB_TOKEN_CODEHASHES is an ALLOW-list that contains EXACTLY the two honeypot templates (0x18449a16... and 0x5faca898...). That whitelists the trap. Both hashes must be DENIED/refused, and no new launcher-family hash added without this analysis. 2) The pre-buy round trip (contracts/BnbRoundTrip.sol via simulate()/check() in src/bnb_live.py) is structurally incapable of catching this and must not be trusted as a honeypot test here: it runs buy+approve+sell in ONE eth_call from a FRESH fabricated harness account (HARNESS 0x00..b0b0b0b0, src/bnb_live.py line 61), whose operator-allowance is 0 (even) so the sell always passes; and the freeze is applied REACTIVELY by a separate operator tx AFTER the buy, so no single-transaction, same-block, pre-buy simulation (nor a two-block EOA sim) can observe a mark that does not yet exist. 3) Add a STATIC detector in the pre-buy path: read storage slot 6; if it holds a nonzero address that _transfer trusts, and the runtime gates transfers on the parity/low bit of allowance[thatAddr][from], refuse the token. 4) Defensive holding guard (detection only, cannot beat the mark): while a position is open, each block read allowance[slot6operator][ourWallet] (operator = SLOAD slot 6) and/or eth_call a real-wallet sell; the instant the low bit is set or the sell reverts with empty data, alarm/halt -- but treat this as post-mortem, not protection. 5) Do not watch Approval event VALUES to detect marking; the arming event emits a decoy amount.

### files

Read-only analysis; nothing in src/deploy/tests/docs was edited and nothing was committed. Repo files cited: /home/user/v2pons/src/bnb_live.py (BNB_TOKEN_CODEHASHES lines 65-66; HARNESS line 61; check() ~line 793; simulate() ~line 839; live_check codehash gate ~lines 800-812), /home/user/v2pons/contracts/BnbRoundTrip.sol (the one-eth_call buy+approve+sell run from a fresh address). Research artifacts written under /home/user/v2pons/research/session_oct14/bnbfreeze/: findings.md (full write-up), code/disasm.py (EVM disassembler), code/tok_2995.asm (our token / 2995-byte template disassembly; freeze at 0x04ce-0x04f5), code/tmpl1365.asm (1365-byte template; freeze at 0x02da-0x02e6), code/rpc.py, code/sim.py, code/prove.py, code/prove2.py (override proofs of the parity rule), code/batt.py (fresh/crowd battery), code/xtmpl.py + code/xconfirm.py (cross-template slot-6 operators and live parity confirmation), code/probe1-4.py (buyer census, storage/allowance reads, marking-tx decode), code/buyers.json. Scratchpad inputs used: /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb_tok_code.hex (our token runtime) and the census file /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/census_PancakeSwap_V2/cache/codes.jsonl (template instances 0xef2622bd... [1365, operator 0xd604540564b6f659de163ad928e29782185da2fd] and 0x314674a4... [2995, operator 0xbd418ce6...]).

## Analyst: data

### finding

The token is not frozen by any window or code rule. The operator freezes every holder outside its own crowd, by sending a transaction 4 to 67 blocks after each buy.

Our trade: we bought at L+52 (tx index 35, first buyer). At block 127550560 (L+70, 18 blocks later), 0xbd418ce6 sent tx 0xc3177267… to the token, at 0.051 gwei with nonce 38811. The call was approve(0x8881bba6…, MAX). That "one approve" you saw is the blacklist call. The token emits a look-alike Approval event: topic0 0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0 (the ERC-20 one ends …c925), with data = the target. Archive eth_calls show our transfer(dEaD,1) works up to block 127550559 and reverts from 127550560 on (d07, d17). In 8 random strangers out of 8, the transfer flips to revert exactly in the block of the operator's approve.

Scale (600,000 blocks, about 3.1 days):
- 554 launches. Sizes: 34 of 1 BNB, 141 of 2.5, 37 of 10, 273 of 15, 69 of 25.
- Every 1/10/25 pool uses the 2,995-byte template (keccak 0x5faca898…, one of the engine's allowed hashes). The 2.5/15 pools use the 1,365-byte template. Both templates are frozen the same way.
- 17,297 buys by 221 addresses.
- The crowd: 120 wallets. Each buys only through the router with 7ff36ab5, tokens to itself, at exactly 0.051 gwei, in 60 to 110 pools. None was ever frozen.
- The other 1,798 (token, buyer) pairs are strangers: 141 bought before their pool's dump. The other 1,657 bought after it (almost all are 3 bot contracts that buy in 519 to 549 pools after the dump).
- 1,615 freezes in 3 days, from 4 operator wallets: 0xbd418ce6, 0xa70b3f34, 0xd6045405, 0x623e7c23.
  - All are sent at 0.051 gwei, the same price as all 554 launches and the crowd's buys.
  - The amount is 0 in 923 of them and MAX in 692; both freeze.
  - Each target is frozen exactly once and none was ever unfrozen. All 1,539 frozen pairs with a balance revert today.

Strangers before the dump (141):
- 134 were frozen while holding.
- 6 got out by selling 5 to 16 blocks after buying. Four of those are one wallet, 0x0b031fcf, via contract 0x1de460f3 (selector 4d819a2a).
- 1 is an aggregator holding 1 wei of dust.
- Delay from buy to freeze (n=135): min 4, p10 8, p25 15, median 26, p75 34, p90 39, max 67 blocks. A wallet that only received tokens by transfer was frozen 3 blocks later.

By offset: holders were frozen in every bucket from +0 to +7,999. +0–19: 25 of 25. +40–59: 2 of 2 (us at +52 and one at +57). +60–259: 14 of 14. +260–999: 40 of 43. +1000 and later: 53 of 57. The rest sold out early.
- Method makes no difference. Frozen buyers used the router's 7ff36ab5 (26, including copycat 0xd9c2e276, which bought at +4..+16 with the crowd's call at 0.05 gwei and was frozen in all 22 of its pools), b6f9de95 (13) and aggregator or bot contracts.
- Recipient type makes no difference: EOAs 119, EIP-7702 EOAs 14, contracts.
- Gas price makes no difference: one buyer at the crowd's own 0.051 gwei was frozen.
- The only exemption is being one of the operator's crowd wallets.

The census week (Oct 4–11) had the same freeze. The first family pool was frozen on Oct 4 at 23:11; 728 freezes hit 281 of the 290 1/10/25 pools. Of 32 strangers who bought before +990, 28 were frozen while holding. The other 4 sold first, 21 to 29 blocks after buying, and were all frozen afterwards; 3 still hold frozen leftovers. Those 4 are exactly REPORT_BNB's "outsider sells" (scratchpad e13). So strangers in the research did sell, but only quick partial or whole exits before the freeze. No stranger ever sold after holding 210 blocks.

What "20 of 20 round trips" measured: the repo's verify/ folders are empty. The script is the scratchpad's bnb/verify/execution_PancakeSwap_V2_on_BNB_Chain__F_lc_83af7929…/code/e09_roundtrip.py. It ran an eth_call buy (7ff36ab5) from a made-up fresh EOA on the state at L+59. Then it ran a sell on the state at L+259, carrying over only that address's balance and allowance slots as state overrides. The output: 20 of 20 sold, and sell out == formula. That proves the code and the V2 math work for an address the operator never saw. It could not see a freeze that arrives later as a separate operator transaction.

REPORT's "reaction to strangers: none seen" only measured crowd buying and the dump timing; it never read the token's own events. BnbRoundTrip.sol (buy and sell in one transaction) is blind to this for the same reason.

Launches continue: there were new ones at blocks 127552413 and 127552946.

### rule

There is no rule inside the transfer logic about time, offset or method. The block is a per-address blacklist that the operator sets by calling the token's approve(target, amount).
- The callers are four non-holder operator wallets: 0xbd418ce6a83995971de9f1cf9f61f345e91aeadd, 0xa70b3f34e3ca7d4665b794ce6bb29168b1d2e40d, 0xd604540564b6f659de163ad928e29782185da2fd, 0x623e7c23c7c228095f94d9bd567eae55cb87a966. Amount 0 and amount MAX both freeze. The crowd's own approve(router) calls freeze nothing.
- It emits the look-alike topic 0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0 with topics (caller, target) and data = target.
- From that block on, any transfer from the target reverts with empty data. That covers a plain transfer() (to 0x…dEaD or to the pair) and the router's transferFrom, so a sell fails with TRANSFER_FROM_FAILED.
- What triggers it: any address that is not one of the operator's 120 crowd wallets and that holds the token, whether it bought (from +4 up to after the dump) or received a transfer. The freeze lands 4 to 67 blocks after the buy before the dump (median 26). Receivers were frozen in as little as 3 blocks. Holders after the dump are frozen with a median delay of 84 blocks.
- Measured: 1,615 freezes in the last 3 days and 728 in the census week. 0 crowd wallets frozen. 0 unfreezes. Today's transfer test agrees on every frozen pair with a balance (1,539 of 1,539).

### expires

The freeze never expires and was never lifted in the data. Each (token, target) got exactly one operator approve, there were no later approves, and no frozen holder ever moved tokens again.
- Today, all 1,539 frozen pairs with a balance revert on transfer(dEaD, 1%) at the latest block (d10). That includes census-week strangers frozen 7 to 9 days ago (d11b: 31 of 31 with a balance revert).
- Our 26,815,492,626,516 tokens (bought for 0.006722 BNB) have reverted since block 127550560, and still do at the head (checked on 5 endpoints).
- Our pool's creator dump is due around +6,800 (25-BNB median +6,836, range +6,567 to +7,186). After that, even an unfrozen balance would be worth almost nothing.
- So: not transferable, and nothing on chain suggests it will become transferable. A recovery would need an operator action that has never been seen.

### safe_entry

There is no safe entry offset.

By timing: every stranger holder before the dump was frozen, at every offset bucket from +0 to +7,999 (134 of 134 holders, plus 28 of 28 in the census week).

By method, recipient type or gas price: there is no exemption.
- Router 7ff36ab5, b6f9de95 and 5c11d795 buyers, aggregators (0c307f76, 27772d13, e21fd0e9, …) and bot contracts were all frozen.
- EOAs, EIP-7702 EOAs and contracts were all frozen.
- Gas price below, at (0.051) and above the crowd's was frozen.
- tx.from == recipient or not makes no difference.
- The crowd's own shape (7ff36ab5 to itself at 0.05 gwei) was frozen 22 times out of 22 (0xd9c2e276).

The only non-frozen buyers are the 120 crowd wallets (identity) and strangers who sold before the operator acted. There were 6 of those in 3 days, selling 5 to 16 blocks after buying, and 4 in the census week, selling 21 to 29 blocks after (all 4 frozen afterwards).

The only hold the data calls safe is 3 blocks or less: the shortest freeze after a buy was 4 blocks (3 blocks for a transfer receiver). On these pools, a 3-block hold at the line's exit (buy +257, sell +260) loses −0.50% gross and −1.05% net. A 3-block hold timed on a crowd wave (around +130 in 1-BNB pools, picked on day 1) made, on day 2, a mean of +8.5% but a median of −1.05% (n=17, 29% win). On 10-BNB pools it made +3.6% (n=11), and on 25-BNB pools −0.4%.
- This is tiny and fragile. The sale must land in block K+2 or K+3, but the engine reads two blocks behind the head. A freeze has already come in 3 blocks once.

The crowd keeps buying after a later entry. Its first buy comes at +63 to +120 (mode +75/+76). The share of its pre-+260 BNB that comes at or after +K (1/10/25-BNB pools):
- +100: 79% / 70% / 75%
- +150: 58% / 42% / 48%
- +200: 24% / 25% / 25%
- +250: 3% / 6% / 4%

After +260 it buys much more, up to the dump: 23.9 / 254.5 / 1,232 BNB over 26 / 25 / 43 pools. But every hold longer than 67 blocks ended frozen, so a later entry cannot reach that buying.

### edge

Repriced on 94 pools: every 1/10/25-BNB pool launched in the last 2 days with L+260 at or before the head (26 of 1 BNB, 25 of 10, 43 of 25).
- Method: exact PancakeSwap V2 replay, the same as the engine's. Our $5 buy is first in block L+K, priced on the USDT/WBNB pair at L+K−1. Every swap and mint up to L+259 is replayed on a copy with our buy in it, and we sell at the start of L+260. Gas is 370,000 × 0.1 gwei.
- Exactness check: our real buy (msg.value 6,722,477,509,199,193 on the reserves just before tx 35) replays to 26,815,492,626,516 tokens, exactly what the pair sent.
- The freeze model: a frozen holder gets nothing back. The survival curve S(h) is the empirical share of the 135 pre-dump freeze delays longer than h.

The dry rule, buy +50 and sell +260 (hold 210 blocks):
- 1 BNB: gross mean +133.98% (median +115.79%)
- 10 BNB: gross mean +35.56% (median +33.77%)
- 25 BNB: gross mean +7.78% (median +6.78%)
- All 94: gross +50.07%, net +49.52%, 97% win. That is about +$2.48 a trade at $5.

With the freeze, S(210) = 0, so every trade is −100% (−$5). With all three sizes traded (about 47 pools a day), that is about −$235 a day, against roughly +$116 a day on paper.

Later entries, still selling at +260 (net if never frozen → net with the freeze):
- +100: +31.7% → −100%
- +150: +18.3% → −100%
- +193: +9.0% → −100% (S(67) = 0)
- +200: +6.5% → −98.4% (S = 0.015)
- +220: +6.6% → −93.7%
- +240: +2.6% → −37.0% (S = 0.62)
- +250: +0.15% → −12.5% (S = 0.87)
- +257 (hold 3, S = 1): gross −0.50%, net −1.05%

No entry offset has a positive expectation.

### fix

1. Stop the line now: set BNB_LIVE=0 for launcher 0xc9b7cc61. It is a stranger honeypot run by the operator, and the dry results only describe what the crowd itself can do. Remove both templates from BNB_TOKEN_CODEHASHES (0x5faca898… for the 2,995-byte token, 0x18449a16… for the 1,365-byte one), or mark them as known traps. The allowlist cannot protect us here because the trap is the template itself plus the operator's wallets.

2. The pre-buy check cannot see this, by design. BnbRoundTrip.sol (buy and sell in one transaction), e09's state-override round trip, and even a multi-block eth_simulateV1 all simulate a world where the operator's freeze transaction does not exist yet. Replace "can it be sold now" with a family-level exit gate built from chain history, run before going live and again every day. Over the last N pools of the family:
   - list every non-crowd buyer that held at least the rule's hold (210 blocks);
   - require that at least 5 of them later transferred or sold successfully (here it is 0 of 134, and 0 of 28 in the census week);
   - for every stranger that still holds, require that an archive eth_call of transfer(dEaD, 1) from its real address passes at the planned exit block.
   This check would have refused the line on Oct 12.

3. Live detector (the engine already reads each pair's logs; add the token's own logs):
   - Treat any approve-shaped log from the token as a freeze when its target is a holder or our wallet and its caller holds nothing. That covers topic0 0x8c5be1e5…eeaa0 here, or more generally any log whose topics include our wallet and that the token emits outside a transfer.
   - Halt the line the first time any stranger in the family is frozen.
   - After each of our buys, eth_call transfer(dEaD, 1) from our wallet every block, and alarm or halt when it reverts.
   These are tripwires only: our wallet was frozen 18 blocks after the buy, and other strangers as fast as 4 blocks.

4. Research method: every verification gets a stranger-exit check. Decode all of the token's events, including unknown and look-alike topics. Test real stranger addresses with archive eth_calls at their later blocks, never state-override fresh addresses. Report "N strangers held at least H blocks and sold" as a gate.

5. Do not trade the 3-block flip. It has a negative median, at most about $5 a day in the best case, and needs a sale inside a freeze delay that has already been 3 blocks.

### files

Everything is in /home/user/v2pons/research/session_oct14/bnbfreeze/data/. Raw caches are in data/cache/ (52 MB, ignored by git). Nothing in src, deploy, tests or docs was touched, and nothing was committed.

The main files:
- d10_table.json and d10_strangers.csv: the stranger table, one row per (token, buyer) with buy offset, method, recipient type, freeze offset and delay, moves out, and today's transfer test.
- d13_tables.out: the frozen-versus-free tables by offset, method, recipient type and gas price, the replay exactness check, the first crowd buy per pool and the short-hold grid.
- d12_reprice.py / .json / .out: the repricing.

Pipeline, in order:
- rpc.py (read-only helper; keyless endpoints only: sentio, blockmachine, pocket, plus the listed ones) and common.py.
- d01_launches.py / .json / .out
- d02_logs.py / .out
- d03_txs.py / .out
- d04_buyers.py / .out
- d05_status.py / .json / .out: a first pass. Its crowd definition left out the gas-price condition, so it wrongly counted copycat 0xd9c2e276 as crowd; d10 replaces it.
- d06_dumps.py / .json / .out
- d07_flip.py: the archive binary search for the block a holder became frozen.
- d08_approvals.py / .out
- d09_freezes.py / .json / .out
- d10_table.py / .out
- d11_census_freezes.py / .json / .out and d11b_census_strangers.py / .json / .out: the census week (Oct 4–11).
- d13_tables.py
- d14_ops.py / .out
- d15_recent.out
- d16_shorthold_oos.py / .out
- d17_flipcheck.out

Research files read:
- /home/user/v2pons/research/session_oct12/bnb/REPORT_BNB.md
- /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/verify/execution_PancakeSwap_V2_on_BNB_Chain__F_lc_83af7929e5a814a2ef2296c29da510961dab2/code/e09_roundtrip.py and its out/e09_roundtrip.out
- …/verify/execution_PancakeSwap_V2_on_BNB_Chain__F_tok_9f0350f062d95ea48f746574ee0b7af7d643/out/e13_outsider_sells.out and e01_fam_pools.json

Scratch copies: /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/dis.py and tok_dis.txt (a disassembly of the token, which uses NUMBER, GASPRICE, COINBASE and a SHA-256 precompile call on an address; left for the code lens).

Note: git shows data/d02_logs.out as modified, so someone else had already committed a copy of it.

## Skeptic

Skeptic review complete. I reproduced every load-bearing claim with my own read-only code (scripts and `.out` logs under `/home/user/v2pons/research/session_oct14/bnbfreeze/skeptic/`: s01–s10). The `findings.md` write was refused for subagents, so the full write-up is below.

# Skeptic review — BNB freeze, token 0x950e6818…bb5 (chain 56)

Read-only: eth_call / eth_simulateV1 / eth_getStorageAt / eth_getLogs only. No key, no transaction. I tried to break each conclusion.

## What I could NOT refute (independently reproduced on the live chain)

1. **The rule is per-address parity of the operator's allowance.** slot 6 = operator 0xbd418ce6…aeadd (read live). `_transfer(from,…)` reverts with EMPTY data iff `allowance[op][from]` is ODD. State-override eth_call (s01): our wallet and a fresh address both PASS for stored 0,2,…,2^256-2 and REVERT for 1,3,…,2^256-1; only bit 0 matters. A non-operator's allowance (even MAX) does nothing. Zeroing slot 6 frees any address. → analyst-1 "parity" and analyst-2 "per-address blacklist" are the same mechanism.

2. **Our wallet is frozen; raw storage = MAX (odd).** Live `allowance[op][us]` = 0xffff…ff. `transfer(dead|pair,1%)` reverts at head on 4 endpoints. The router's `transferFrom(us,pair,1%)` reverts with the same empty data; forcing `allowance[op][us]=0` (even) makes BOTH pass in simulation (s10) → the TRANSFER_FROM_FAILED sell is this gate reading `from=us`, not a router-allowance problem.

3. **The mark is written by the operator's `approve(victim, oddValue)`.** s04 [D]: operator `approve(fresh,odd)`→can't transfer; `approve(fresh,even)`→fine; only parity is tested. Our arming tx is 0xc3177267… at block 127550560 (L+70, 18 blocks after our buy), `approve(0x8881…fcb, MAX)`, 0.051 gwei. Its log topic0 is 0x8c5be1e5…**eeaa0** (look-alike; real Approval is …**c925**), data = our address. The "decoy amount 779315887…219" that analyst-1 flagged is exactly `int(ourAddress)` — the look-alike log's data word is the target, not a value. Across 1,615 freezes the amount word is 923×`0x…0001` and 692×MAX — all odd (s03).

4. **Both whitelisted templates are the same honeypot.** 2995-byte codehash 0x5faca898… (our token) and 1365-byte codehash 0x18449a16… (live instance 0xddf1a058…, operator 0x623e7c23…) both show even=pass / odd=revert and slot6=0=free, live (s09). The engine's `TOKEN_CODEHASHES` (src/bnb_live.py:65-66) is an ALLOW-list containing exactly these two hashes — it whitelists the trap.

5. **No temporal term; does not expire.** Only storage flips the outcome. Far-future eth_simulateV1 (+500,000 blocks / +5 days) still reverts (s10, endpoint bm). In the data, each (token,target) got exactly one approve, 0 un-freezes, all frozen pairs with a balance still revert at head.

6. **Safe entry for our profile = none.** Of 141 strangers who bought before the creator dump, 135 were frozen; the 6 "escapees" all SOLD within 5-16 blocks of buying. Frozen at every buy-offset bucket +0…+7999 (s06). 0 of 120 crowd wallets ever frozen. 0 before-dump strangers held ≥210 blocks and sold unfrozen. Our wallet: bought +52, armed +70 (d17 archive flip confirms: ok before +70, reverts from +70 on). Live, a crowd wallet transfers fine while our wallet and a different frozen stranger both revert (s08/s09).

## Where I sharpen / qualify the analysts (does not change the verdict)

- **"No stranger ever sold after holding 210 blocks" is not literally true.** 51 pairs held ≥210 blocks and sold unfrozen — but all 51 are ONE after-dump dust-sweeper contract 0x220794f72f (buys near-zero value in 519 pools; frozen in 464, missed in ~55 ≈ 11%). It bears no resemblance to the engine's profile (first in, 1/10/25 BNB, sell at +260). The operator's catch rate on a trivial after-dump sweeper is ~89%; on an early meaningful buyer it was 135/135. Verdict unchanged.
- **The two freeze-delay medians (26 vs 67) differ only because they measure different populations** (before-dump vs all holders). Both agree the fastest freeze was 4 blocks after a buy (3 for a transfer receiver); ours was 18. For the engine the only number that matters: faster than a +260 sell placed from +50, every time.
- **"amount 0 also freezes"** applies to the 1365-token operators in analyst-2's data, but a literal `approve(x,0)` writes an EVEN value, which I confirmed does NOT freeze on a live 1365 instance (s09). What freezes is odd parity; the 923 `0x…0001` approves are the common freeze, not zero.

## Re-priced edge (verified against d12; replay matches our real buy to 0.009%)

Dry rule buy+50 / sell+260 over 94 recent 1/10/25 pools: gross +50.1% mean, 97% win — but survival S(210 blocks)=0.000, so **with the freeze every trade is −100% (−$5 at the $5 stake).** No entry offset is positive: +100→−100%, +200→−98.4%, +240→−37.0%, +250→−12.5%, +257 (hold 3)→−1.05%. The only non-negative region is a 3-block flip (median −1.05%; best out-of-sample day +8.5% mean / −1.05% median, 29% win on 1-BNB pools) — and the shortest observed freeze was 3-4 blocks, inside that window, while the engine reads two blocks behind the head. Not tradeable. At ~47 pools/day the live rule loses about **−$235/day** versus +$116/day on paper.

## Does the stuck $5 unlock?

**No.** There is no path through the token's own logic that makes our tokens transferable — the gate reads `from=us` regardless of recipient, amount, method, or time, and I confirmed the router sell hits the identical gate. The only lever is the operator writing an EVEN allowance to our wallet (another approve), never observed for any of the 1,539 frozen holders and not something an adversary does. The even/slot6 "lifts" in my tests are **state-override simulations only** — they do not change real chain state. Treat the 25-BNB position ($5) as a permanent −100%. No transaction should be sent chasing it, and none can recover it.

# Decision for the owner

**Keep the BNB line halted for good against this launcher family (0xc9b7cc61).** This is not a parameterizable edge with a bad tail — it is a discretionary, operator-triggered −100% that deterministically targets the earliest, largest buyer, which is precisely the engine's profile. One marked launch erases a long run of +L50/+L260 gains, and marking is at the adversary's will, not probabilistic. No entry offset, stake size, or hold window has positive expectation. "Resume with changes" is not viable here: the pre-buy round-trip (contracts/BnbRoundTrip.sol, HARNESS 0x…b0b0b0b0 at src/bnb_live.py:61) is structurally blind — it runs buy+approve+sell in one eth_call from a fresh account whose operator-allowance is 0 (even) and the freeze arrives as a later, separate operator transaction, so it will always report "sellable." No single-transaction or two-block pre-buy simulation can see a mark that does not yet exist.

Concrete changes if the owner wants the code hardened rather than just the flag off:
1. **Deny, don't allow, both template hashes.** src/bnb_live.py:65-66 currently allowlists 0x5faca898… and 0x18449a16…, which are the two honeypot templates. Refuse them; never re-add a launcher-family hash without this analysis.
2. **Stop trusting the pre-buy round trip as a honeypot test** for this family (reason above).
3. **Static pre-buy detector:** read storage slot 6; if it holds a nonzero address the runtime trusts, and transfers gate on the low bit of `allowance[thatAddr][from]`, refuse the token. (Both templates match.)
4. **A family-level exit gate from chain history** (what the single-tx sim cannot provide): over recent family pools, require that ≥N non-crowd buyers who held ≥210 blocks later sold successfully (here it is 0 of 135) before going live, and re-check daily. This would have refused the line on Oct 12.
5. **Live tripwire only (cannot beat the mark):** after any buy, eth_call `transfer(dead,1)` from our wallet each block; halt the instant it reverts with empty data. Do not watch Approval event amounts — the arming event logs a decoy.

Recoverable stuck value: **none.** Record the $5 as a realized −100% loss.

Artifacts: `/home/user/v2pons/research/session_oct14/bnbfreeze/skeptic/` — rpc.py, s01_rule.py/.out (parity proof), s02/s04_arm/more (arming + far-future), s03_amounts.out (odd-parity of all 1,615 freezes), s05b_archive.out (archive flip at +70), s06_table_audit.out (escapees, long-holders, 0 crowd frozen), s07_longholders.out (the single sweeper), s08/s09 (live crowd-OK + both templates), s10_final.out (router transferFrom gate + no temporal term).
