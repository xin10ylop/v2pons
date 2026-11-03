# Four chains searched by buyer: Robinhood, Base, BNB, Ethereum (Nov 3)

**Asked:** "you are not searching well ... re search well, and re check base bnb and robinhood, and ethereum" (Solana excluded). Find a
blind, scheduled bot: one that buys every launch of its line at a fixed delay whatever anyone bought before it.

## Method

`buyerlab.py` (widened since REPORT_STRUCT) reads every pool the census saw created and groups every early buy by its buyer, not by the
launch:

- **Who bought.** For a public router, the buyer is the transaction's sender. A contract called by 6 or more different wallets is a router
  too, so its callers become buyers. Every V2, V3 (Uniswap and PancakeSwap) and v4 pool is read.
- **Scheduled.** Within 3 blocks of its median offset in most pools, at one size.
- **Blind.** Within a token-code line, outsiders are wallets other than the launcher and the line's crew (buyers in 10%+ of its pools).
  The test compares two rates: P(it buys | an outsider bought first) against P(it buys | nobody did).
- **Front.** Buy at max(launch + 2, its buy − 5), sell after its buy, on the recorded reserves.

Each lead was then followed pool by pool. `lineprobe.py` gives every swap with its sender, the pulls, and what the crew did when an
outsider came first. On Ethereum, `eth_simulateV1` on archive RPCs ran real sells at the pools' historical state.

| chain | days | pools | buyers in 15+ pools | output |
|---|---|---|---|---|
| Robinhood | Nov 1-2 | 5,511 | 554 | `buyerlab_rh.out` |
| Base | Nov 1-2 | 4,572 | 108 | `buyerlab_base.out` |
| Ethereum | Nov 1-2 | 485 | 44 | `buyerlab_eth.out`, `census_eth.log` |
| BNB | Nov 2 | 6,612 | 550 | `buyerlab_bnb.out`, `census_bnb_20261102.log` |

## Answer: no blind scheduled buyer worth trading on any of the four chains

Every scheduled buyer with real size is the launcher's own, and every one of them is defended against outsiders. The defences differ:
a pull, a blacklist, or the buyer stopping. The blind buyers are routers or traders with no schedule, or they are tiny.

| lead | a day | paper | verdict |
|---|---|---|---|
| **Ethereum V2, token 1,852 B** (launch: V2 router `addLiquidity`, 260 B); 22 crew wallets buy fixed sizes in a fixed order (0.01 at +2 ... 0.4 at +33 ... 0.2 at +133), ~6 ETH into a 5-8 ETH pool; LP burned at +486..+634 | 12 | front in at +2, out at +145: **+230% at 0.05 ETH, +162% at 1 ETH, worst pool +140%** (`ethride.py`) | **Trap: outside buyers are blocked from selling within 1-2 blocks** (`ethblock.out`). The token calls a controller (`0x610b10d3…`, selector `0x478d3305`) on every transfer. Six real outside buyers were checked block by block. Each could sell at the end of its buy's block, and sometimes one block later. After that its sell reverts (`TRANSFER_FROM_FAILED`), while a fresh wallet at the same state still sells (`ethsim.out`: no tax, −0.6% round trip). A seventh held no tokens by then. No outsider ever sold a real amount. For one of them (0.01 ETH at +5), the block was traced: two blocks after its buy, wallet `0xd6c29dbf…` sent the controller a call (`0xab1b4fa3`) whose 67-byte argument is opaque (the blocked address is not readable). A front would be blocked before the crew's buys come. |
| Ethereum V2, token 4,642 B (`addLiquidityETH` 196 B); 20 crew wallets of ~0.02 ETH | 37 | front +13-15% | No schedule (the wallets' offsets spread over +7..+60). Other crews take the pools where they buy first (`lineprobe_eth_4642.out`). |
| Ethereum `0x4313c378` | 10 | +88% (n 14) | A sniper bot's contract called by 16+ wallets, not a scheduled buyer |
| Ethereum lines down to 6 pools (`buyerlab_eth_min6.out`, 111 buyers) | 3-6 | +9-134% | Nothing new. The 1,764 B line's three blind buyers buy 0.03 ETH at no fixed time (0-43% within 3 blocks), 3-4 pools a day. `0xba412d8b` and `0x90c496de` are sniper contracts with 10+ callers. |
| **Base v4 2,180 B** (the 0.501 ETH timer line); three wallets at +7 (0.01), +11 (0.01), +15 (0.2) | 100 | front +97% | Trap, already known (REPORT_NOV2). 211 of 212 pools never had an outsider. In the one that did (0.0144 ETH at +12), the 0.2 buy never came and the launcher pulled at +13 (`lineprobe_base_2964.out`). Every pool is pulled by its launcher within 300 blocks (about +250). |
| Base blind buyers (`0xbfe36fd4`, `0x76ff501f`, `0xfdf682f5`, `0x8f10b468`) | 14-382 | −11.7% to +2.1% | Unscheduled, or a 0.014 ETH buy at +3 |
| **Robinhood v4 fee 0, 1,572 B** (REPORT_STRUCT's untested self-buy lead); the launcher buys its own pool 0.2-2 ETH, 1-5 times from +200..+550 | 15 | - | **Pulls on any outside buy** (`lineprobe_rh_1572.out`). In 11 pools a dust bot (`0xa96b7baa`, 0.0004 ETH) bought after the launcher's first buy. The launcher then stopped buying and pulled 32-98 blocks later in all 11. In the 18 pools with no outsider, it kept buying (1-5 times) and pulled 2 within the 900-block window. |
| Robinhood launchpad `0xbbf5c604` (REPORT_STRUCT's other lead) | 9 | +1,067% | Not a seat. The pair is created first, but its liquidity (0.17 ETH) is added in the same transaction as the launcher's 0.4 ETH of buys (`lineprobe_rh_launchpad.out`), so there is no pool to buy into before them. |
| Robinhood 1,380 B (`modifyLiquidities` launches, operator A) | 17 | front +5-7% | Known. Three crowds of 15-40 wallets take turns on pools at random offsets (+400..+2,000), so there is no schedule (`lineprobe_rh_opA.out`). |
| Robinhood blind buyers (`0x65050a9b`, `0x9689992f`, `0x00000000e91f`, ...) | 8-44 | +4-11% | Routers and traders whose first buys spread over thousands of blocks (0-13% within 3 of their median) |
| Robinhood 5,274 B crowd (10 wallets × 0.125-0.15 ETH, 124 pools a day) | 124 | front +3.2-3.5% | Reacts: it buys in 2% of the pools where an outsider came first, against 37% clean |
| Robinhood `0xf175f071` | 24 | +7.5% | Blind and scheduled (+3, 96% within 3), but 0.005 ETH a buy |

**BNB** (Nov 2, PancakeSwap V2 / V3, Uniswap V2 / V3 / v4):

| lead | a day | paper | verdict |
|---|---|---|---|
| **BNB V2, token 4,050 B** (PancakeSwap V2 `addLiquidityETH`, 2.5 BNB); about 25 crew wallets buy ~0.27 BNB each at no fixed time from +80 to +1,000 (0.45 s blocks); LP burned at about +1,460 | 54 (Nov 2), then **stopped** | front, sold at +1,000: +313% at 0.05 BNB, +97% at 1 BNB (`ethride_bnb_4050.out`) | **A team-list token with one exit: a zero-gas-price sell** (see the section below). The crowd buys in every pool, even after an outsider, but every crew wallet is on the token's team list. While the 7-day lock is on, an outsider's sell reverts `Hush()` unless `tx.gasprice` or `block.coinbase` is 0. Eleven outsiders bought 0.001 BNB or more on Nov 2. Eight never sold. Three sold at 3.2-4.5x, all with zero-gas sells in bundles paid by one trader. The line launched every ~18 minutes from 06:00 to 15:00 UTC on Nov 2 and stopped right after the third of those exploits (`bnbsim.out`: no launch in the 7.5 hours before the check). |
| BNB V2, token 2,046 B; a rotating crowd of 25+ wallets through router `0xa3e0e540` | 210 | front +6-8% | **Pulls on any outside buy**: in 27 of 27 pools where an outsider bought first, the launcher pulled 2-7 blocks after that buy (`lineprobe_bnb_758b.out`). |
| BNB earlier (old method): the 2.433 operator's own token | 481 | - | 19 of 19 real outsiders pulled (the first BNB run, Nov 3 morning) |

## BNB 4,050 B: how the exit works (Nov 3 afternoon)

Asked: "understand it, take days if you need". `minievm.py` (new) is a small EVM interpreter that runs the token's own code (4,050 B,
Solidity 0.8.26, no external calls) on its real storage. It shows every storage read and every branch, so each rule below is the
code's own decision (`bnbtoken.out`). The BNB node agrees (`bnbhush.out`).

**The rule.** The token is an OpenZeppelin ERC-20 with a check in its transfer:

| transfer | while the lock is on | after it, or before `pose` |
|---|---|---|
| buy (the pair sends) | allowed, no check | allowed |
| sell (to the pair) by a team wallet | allowed | allowed |
| sell by anyone else | reverts `Hush()`, **unless `tx.gasprice == 0` or `block.coinbase == 0`** | allowed |
| wallet to wallet, team | allowed | allowed |
| wallet to wallet, anyone else | reverts `Hush()` (no gas-price escape) | allowed |

The storage behind it:

- Team list: mapping slot 7, set by `setTeam(address[],bool)`, which emits `0x03b34e9b`.
- The pair: slot 6, set by `moor(address)`, which emits `0xea08d792`.
- The lock: `pose(true)` stores a flag and a horizon of now + 7 days in slot 8, XORed with a 32-byte constant (`0x5a…5a`) kept in the
  code. `horizon()` and `veiled()` read it back.

A default `eth_call` or honeypot checker runs at gas price 0, so it shows a working sell. That is most likely why the escape is there.
On BSC, though, a real transaction can also have gas price 0: a builder includes it in a bundle whose other transaction pays.

**The timeline, all 51 pools** (blocks of 0.45 s after the launch; median and range):

| step | offset |
|---|---|
| team set (52 crew wallets a pool, 154 across the line) | −8 (−11..−5) |
| pair moored | +30 (+23..+36) |
| lock on (`pose`) | +43 (+34..+53) |
| the crowd's first buy of 0.05 BNB+ | +79 (+71..+89) |
| LP burned | +1,478 (+1,440..+1,573), about 11 minutes |

The lock runs 7 days, so for the whole life of a pool an outsider can buy but can only sell at gas price 0.

**The three outsiders who sold** (pools #18, #44 and #51 of the day's 51):

- Each used a brand-new wallet with 0 BNB, delegated by EIP-7702 to MetaMask's stateless delegator (`0x63c0c19a…`), and acted through
  the DelegationManager's `redeemDelegations` (`0xdb9b1e94…`).
- Each wallet was used for one buy and one sell, both at gas price 0 (`effectiveGasPrice` 0): a type-4 buy at +38..+41 (0.27-0.31 BNB,
  just before `pose`), and a type-1 sell at +460..+1,091 for 1.0, 0.98 and 1.32 BNB.
- Each zero-gas transaction sits beside a transaction from `0x08a69cea…` (242 transactions, 0.4 BNB) to PancakeSwap's Universal Router.
  That transaction carries the stake as value on the buy, and pays 5.1 gwei on the buys and 12.7 gwei on the sells: the bundle's fee.
- 48 Club's address `0x4848489f…` appears in three of the six blocks (a payment to it, or its block marker), so the bundles went at least
  partly through 48 Club's builder.
- The line stopped right after the third of these exploits.

**What a seat would need:**

- A BSC path: the engine has none. It would need PancakeSwap V2, BNB funding and gas.
- The buy: any time from launch to about +79, at a normal gas price (buys are never checked).
- The sell: inside a builder bundle at gas price 0, from the wallet that holds the tokens, with another transaction paying the builder.
- Shell wallets with no BNB are how the competitor did it.

On the Nov 2 tapes, a sell at about +1,000 paid +313% at 0.05 BNB and +97% at 1 BNB (`ethride_bnb_4050.out`). The competitor took
3.2-4.5x on 0.3 BNB.

**Against it:**

- The line is offline.
- The operator writes a new token for every pool, so one deploy can remove the escape.
- A competitor already runs this exact trade.
- `docs/BASE_PROMPT.md`: "A pool whose exit test fails is not traded. Do not try to get around a hook that blocks sells." A gas-price-0
  sell is getting around a sell block. Whether to change that rule is the user's call.

## What this says

Four chains and roughly 17,000 pools turned up the same thing. A buyer that comes at a fixed delay with real size is the launcher's own
money pumping its own pool. Every such launcher watches for outsiders and defends:

| defence | lines |
|---|---|
| pulls the pool | Base timer, Robinhood fee 0, BNB 2,046 B, the 2.433 operator's 3.0 ETH line |
| stops buying | Robinhood 5,274 B crowd, the V3 crowd |
| burns, blacklists or freezes the outsider's tokens | C-1 (live, Nov 3), Ethereum 1,852 B, BNB 4,050 B |

The 2.433 seat worked while its bot did not check; nothing found now behaves like that. The paper numbers on these lines (+97%, +230%)
are what they look like before the defence. Each was large because nobody can take it.

## Tools

- `lineprobe.py CHAIN DAYS TO SELECTOR LEN [TOKEN_LEN] [WIN]`: one launch line pool by pool. It shows the crew, the anchor buyer, and
  the pools where an outsider bought first: whether the anchor still bought, and when the pool was pulled.
- `ethfull.py`: the Ethereum 1,852 B line followed to its LP burn.
- `ethride.py`: its front replayed with our trade in the pool.
- `ethsim.py`: a fresh wallet's buy and sell through `eth_simulateV1` at historical states.
- `ethblock.py`: real holders' sells against a fresh wallet's, block by block after the buy.
- `ethfull.py CHAIN LINE_JSON OUT_JSON [BLOCKS]` also follows a BNB line (`linefull_bnb_4050.out`). `minievm.py`: a small EVM that runs
  one contract's code on its real storage with a trace. `bnbtoken.py`: the 4,050 B token's rule and the line's timeline. `bnbhush.py`:
  holders' sells and moves on the node at gas price 0 and 0.1 gwei. `bnbsim.py`: a fresh wallet's buy and sell on the line's live pools (none now).
- BNB has no free archive state (publicnode wants a token; `bsc-dataseed` answers only the latest state).
- `eth_simulateV1` with history works on `eth.drpc.org` and `ethereum.publicnode.com` (publicnode answers 403 under load);
  `rpc.mevblocker.io` has no archive state.
