# Someone is winning: the operator's fee-0 pump pools (Nov 16)

**Challenge:** if 2.433 worked, something should work; "nothing works" can't be right.

Fair. So instead of hunting a 2.433-shaped line, I ranked **every wallet** by realized native across all Robinhood pools Nov 10-11 + 14-15
(`walletpnl.py`, 9,047 pools).

## The blunt answer, both ways

- **The market is shut to the typical outsider.** Of 3,813 independent wallets trading 5+ pools, the median realized **-2.2 ETH** and only
  21 were net positive. Most buyers lose.
- **But a few win, independently.** After stripping accounting artifacts (mis-sided pools showing impossible ETH), the clean winners are
  small and selective: `0xf2c69db0` +1.2 ETH (sold out of 56% of 16 pools), `0x00000000e91f` +1.3 (an MEV bot), `0xbb75f6e4` +0.19 (75% exit).
  Not a blind-bot seat -- skilled, selective trading.

## What the winners trade: the operator's fee-0, no-pull pools

Both `0xf2c69db0` and `0xbb75f6e4` make their money on one cluster: **fee-0 pools, launched by a handful of the operator's launcher
contracts** (`0x1531efda`, `0x387a453d`, `0x92475293`, `0xd83ba5ff`, `0x7ed598bc`), token code 3,248 B. On those pools they win repeatedly
(+20, +27, +58, +136, +162, +182, +278, +322%); their losses are on other token types. I missed this before because these pools launch
under many different launcher templates (so they never grouped as one "line") and the winners recur across pools (so my "outsider" filter
counted them as crowd).

On the 16 pools of these winning sub-lines:

- **fee 0, 0 of 16 pulled**, real demand arriving after entry (native bought after +20: median 0.7-14 ETH per pool).
- **Not a honeypot**: a fresh FlipRelay buy+sell round-trips (`deploy/relay_sim.py`); the ~-6% is price impact in now-drained old pools at
  fee 0, not a block. The 3,248 B *bulk* template (`0x58daec31` 1444 B, 144 pools) is different -- fees of 10-90% that eat the trade; only
  the fee-0 sub-lines pay.
- **22 distinct wallets net positive** in these 16 pools, including independents that launch nothing.
- **But**: the biggest winner in all 16 is `0x65050a9b` -- the 2.433 operator's own decoy-buy router. So this is that operator's ecosystem,
  and the demand you'd sell into is largely its own decoy pumping. Reliable (no pulls) but operator-controlled.

## Verdict

The honest version of "something works": yes -- the operator runs fee-0 pools it pumps with its decoy router and does not pull, and both
its own wallets and independent snipers sell into that pump at a profit. It is 2.433-shaped and the exit is real. The risks are that the
sample is thin (~4 pools/day), the demand is the operator's own (it can stop or turn on us, as the V3 crowd did on our live buy), and the
reaction to *our* buy specifically is untested.

## Next

Build an engine entry for the ride (arm on a fee-0, no-hook pool of these launchers once the decoy/crew buys; sell into the pump), dry-run
it on the live feed, then a small live probe. Live carries the operator-controlled-demand risk above.

## Tools
- `walletpnl.py DUMPS [MIN_POOLS]` -- rank every wallet by realized native; tags operator routers and launchers.
