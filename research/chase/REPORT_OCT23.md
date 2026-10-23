# The 2.433 operator, re-traced (Oct 23, 11:30 UTC)

Asked: check the 2.433 operator again on all its lines, trace its wallets back to new and original ones, and find where it runs now.

**Answer: it is not running anywhere.** It has sent nothing since Oct 19 18:33 UTC. Its money is still parked on BNB: 26.65 BNB in
`0x23055b43`. No chain in the census shows a line with its shape, wallets or routers. The one fresh scripted line found (Base, 0.5013 ETH)
belongs to someone else and reacts to outsiders within 2-3 blocks. The hourly watch now also covers the new admin wallet found below.

## How its wallets work (trace_bsc.py, NodeReal transfer index)

- **One fixed, ordered list of launch wallets, walked in order.** Each wallet takes the line's whole bankroll from the one before it, runs
  one launch in exactly 7 transactions, and passes everything on:
  1. funds the router with the fleet's money (selector `7422a284`, which also deploys the 777 token);
  2. approves the token;
  3. approves Permit2;
  4. mints 10.5333 BNB through the PositionManager (`ac9650d8`);
  5. approves again;
  6. pulls through the router (`a0f7978d`);
  7. sends everything to the next wallet.
- Every launch wallet sampled (50 of 754) has nonce 14 on BNB and 7 on Robinhood: one pass on Robinhood, two on BNB. Nonce 0 on all 27
  other EVM chains.
- **The two BNB passes run in the same order.**
  - Sep 24-26: 7.5333 and 1.5333 BNB pools, through its old router `0x07cb6161`. That router's code is byte-identical to its Robinhood
    router.
  - Oct 15-19: 10.5333 BNB pools, through a new router `0x37dc44b6` (22,816 B).

  Example, Oct 19: `0xfff2e38e → 0xb2f2d149 → 0x17e7b938 → 0xb5c18ddf → 0x5b3510c1 → 0xa01bb8f4 → … → 0xd76f7b2e → 0x23055b43`. On Sep 26 the
  same wallets ran in the same order and the pass continued `0x23055b43 → 0x4a46c0f1 → 0x6cbbadec → 0x2a245cf3 → 0xe7c804b4 …`.
- **The October pass stopped at `0x23055b43`.** At 18:33 Oct 19 the fleet swept its BNB into it, and nothing has moved since. If the
  line resumes on BNB, the next wallet is `0x4a46c0f1`.

## Where the money came from (evm_hops.py, deployer.py; archive state, no index needed)

| when (UTC) | hop | what it shows |
|---|---|---|
| Oct 14 19:27 | `0xf84491a6` → `0xd754c018`, 5.07 ETH on Base | launch-list wallets: both have nonce 11-12 on Base, 6 on BNB, 8 on Robinhood |
| Oct 14 19:32 | `0xd754c018` → **`0x219a5d525c4acc924bcbbeca1c2d48833815fd96`**, 7.5 ETH | **a new admin wallet**, not in any earlier list |
| Oct 14 19:42 | `0xd754c018` launches a 777 token through the Base router `0x987d5db8` | the Base stretch our base-0.2 engine traded |
| Oct 14 19:49 | admin → `0x33f24cf4`, 7.48 ETH | the head of its Base launch chain |
| Oct 15 10:22 | admin → `0xef4fb24a`, 8.226 ETH on Base; 26.86 BNB arrives on BNB 28 s later | a bridge: `0xef4fb24a` is a contract holding large balances on 20+ chains |
| Oct 15 10:24-10:27 | admin → `0x1382a772`, 26.86 BNB; admin deploys the router `0x37dc44b6` (its nonce 1) | the head of the October BNB pass and its new router |
| Oct 19 18:33 | the pass ends at `0x23055b43`, 26.65 BNB | in 26.86, out 26.65 over 750 pools: about break-even before gas, likely why it stopped |

- The admin `0x219a5d52` has been used only on Base (nonce 3) and BNB (nonce 4). Its CREATE addresses at nonces 0-5 have no code on any
  chain except the BNB router.
- Its routers exist only at the known addresses:
  - Robinhood `0x1cbaf24d`, BNB `0x07cb6161` and HyperEVM `0x948f63b2`, all byte-identical (20,443 B);
  - Ethereum `0xfac75d23`;
  - the October BNB router `0x37dc44b6`.
- `0xfac75d23` is admin `0x5b2b20e1`'s nonce-0 address, so the same address also holds other contracts on Base (Jun 2026) and BNB
  (Nov 2025).

## Every v4 launch on 28 chains, last 24 h (v4census.py)

The census reads the Initialize logs and the launch transaction's value for every native pool. The operator launches every pool with
one fixed amount, often ending in 33 (2.433, 4.133, 1.533 ETH; 10.5333, 7.5333 BNB).

- **No pool with its shape** (fee 5000, tick spacing 100, native, with or without a hook) on any chain, and no launch value ending in 33.
- Families with a fixed launch value from many senders:
  - Robinhood: the volume bot's 3.0 ETH (775 pools) and 5.0 ETH (184) lines, known since Oct 20.
  - BNB: 0.003 BNB dust pools.
  - Base: two lines, below.
- Nothing on Arbitrum, Optimism, Unichain, Polygon, Avalanche, Ink, World Chain, Monad, HyperEVM or the rest.

### Base, 0.5013 ETH every 10 minutes (v4line.py, 119 pools)

- **The pool:** fee 100, tick spacing 1, no hook, one fixed opening price. Running since Oct 22 15:43 UTC.
- **The fleet script, identical every pool:** three wallets (`0x1c89b0da`, `0x5a909245`, `0xf09b59fc`) buy 0.0101 at +5 and 0.0101 at
  +9, buy 0.2007 at +13, sell 0.1613 at +20, buy 0.1507 at +27. The pull comes at a median +251 (8.4 min).
- **Its launch wallets:** a 7-transaction pass-on chain like the operator's, but its own:
  1. 0.2103 ETH (exactly the fleet's net buy) to `0xe162c901`;
  2. deploy the token;
  3. renounce ownership;
  4. approve;
  5. mint 0.5013 ETH;
  6. pull;
  7. pass about 0.898 ETH on.
- **History:** walked back 30 wallets, the chain ran on Oct 13 (11:00-14:40) and then sat 9 days on one wallet before resuming. No
  wallet, router or bridge hop links it to the 2.433 operator.
- **It reacts.** All 4 pools where anyone else bought (0.0004 to 0.083 ETH, at +8 to +163) were pulled 2-3 blocks later. The 114
  pools nobody else touched were pulled on the timer. No seat.

### Base, 1.2001-1.2010 ETH, fee 0 (534 pools a day)

- About 300 swaps per pool from one-time wallets: a volume bot.
- Pulled at about +354 blocks, earlier in some pools (+38, +106, +135).
- With one-time wallets, its fleet cannot be told from outsiders. Same family as the Robinhood volume bot, which pulls 5-21 blocks after
  an outside swap. Not worth a seat.

## The watch

`watch2433.py` (and the hourly scheduled task's embedded copy) now also checks:

- the admin `0x219a5d52`;
- `0x4a46c0f1`, the next wallet of its BNB launch chain (Robinhood baseline nonce 7).

Run at 11:34 UTC: quiet everywhere, 26.65 BNB still parked.

## Tools added

- `trace_bsc.py`: breadth-first BNB money trace through NodeReal's `nr_getAssetTransfers`.
- `evm_hops.py`: an EOA's first funding and each of its transactions, from archive state alone (Base has no free transfer index here).
- `deployer.py`: a contract's creation block and deployer.
- `v4census.py`: every v4 pool on 28 chains, with launch-value families and the operator's shape.
- `v4life.py`, `v4line.py`: one family's pool lives, fleet and outsider reactions.
