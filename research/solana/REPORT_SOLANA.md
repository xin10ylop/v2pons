# Solana, Oct 22 2026: the first census for pump-and-pull lines

Raydium's creator-funded pools, listed from the creation-fee accounts (AMM v4 `7YttLkHD…`, CPMM `DNXgeM9E…`); trades from Helius's
parsed history. Scripts: `census.py` (7 days of creations, creators, funders, pulls), `lines.py` (groups), `trades.py` (every trade on
selected pools), `linecheck.py` (replays per line), `linehist.py` (a line's history from its funder).

- AMM v4 is nearly unused for new pools (~5 a day); CPMM: 771 creations in 7 days, 620 with a SOL side, **409 pulled (66%), median 17 min**
  after creation. Most are 0.1-0.3 SOL. Raydium LaunchLab's migrations (`RAYpQbFN…`, 24-100 SOL) are not pulled.
- Lines that pull every pool: creator `6RsDQGpH…` (17 pools, 7-19 SOL; 78 fleet wallets making hundreds of dust trades, the price
  collapsing before the pull), creator `aPTS9Ki2…` (9 pools, 1.5-9.2 SOL; pulls 3-35 s after outside buys in several pools), and
  **funder `29giReftu9BmqqQhLzHUSzVyNmg8ifJNFeBMWjPPmZ4h`**.
- **The 29giReft line** (8 pools Oct 15-21, its whole 30-day history; the funder also funds 5 fleet wallets with 1-5 SOL at a time):
  a fresh wallet gets 11-12 SOL 2-23 min before its pool; the CPMM pool holds exactly 10 SOL and opens 55-57 s after creation (once
  122 s); the fleet buys 1-5 SOL three or four times from +88-214 s (price x3-x5.5); nothing then until the pull, 8-68 min after
  creation. Outsiders who bought after the pump held into the pull and lost (11 of 12). One sniper bought at the open (+55 s, 0.059 SOL)
  and sold 9 s later: the fleet still came and the pool ran its course; two mid-life buyers sold at no reaction.
- The seat on paper (bought at the open before the fleet, our impact replayed, sold after the fleet's last buy, fee 0.25% assumed):
  0.5 SOL +8.0 SOL over the 8 pools (+201%), **1 SOL +14.4 SOL (+180%), every pool won**, 2 SOL +23.9 SOL (+149%). Unknown: whether the
  operator skips or pulls when a real stake buys before its fleet (Base V2's fleet skipped our pair, Oct 21); the line is a week old
  and launches about once a day.
