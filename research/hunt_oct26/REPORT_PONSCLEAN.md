# Are the four Pons copy-trade wallets clean? (Nov 18)

The four wallets the copy-trade study (another session, Pons bonding curves on Robinhood, Oct 19 - Nov 18) passed:
`0x9a3955a1`, `0x5bc235ac`, `0x9e0771d4`, `0xc54d3914`. "Clean" here means: trading coins they have no hand in. Checked from chain logs
and current state (`ponsclean.py`, output `ponsclean.out`), last 4 days of trades (`0x9e0771d4`: Nov 1-9, its active window).

| wallet | what it is | buys after launch | coins / creators | its own launches | off-curve tokens | verdict |
|---|---|---|---|---|---|---|
| `0x9a3955a1` | 14 KB bot contract, signed by several keys (mostly `0x1e2d6995`, hardcoded in it) | 0.5 s median | 136 / 136 | 0 | none | clean |
| `0x5bc235ac` | EOA that holds and sells; buys come from its own buy contract `0x610de2b5` (buys for no one else) fired by 8+ rotating keys, sometimes from the public `0x65050a9b` router | 0.7 s | 99 / 97 | 0 | airdrop spam only (round amounts of non-Pons tokens) | clean |
| `0x9e0771d4` | EOA using a public bot router (`0xd6d35b56`, 561 users a day) | 28 s | 198 / 198 | 0 | 16 from v4 buys, 3 single transfers | clean, but stopped Nov 8-9 and empty |
| `0xc54d3914` | upgradeable proxy contract, signed mostly by `0xb45d5c06` | 0.4 s | 22 / 22 | 0 | 1 from a DEX pool | clean |

- **Nobody bought a coin it or its signer launched,** none bought inside a launch transaction or launch block, and the creators are
  almost all one-launch wallets.
- **Between them:** no shared signers. `0x9a3955a1` and `0x5bc235ac` bought 22 of the same coins, 17 within 2 blocks of each other:
  two snipers firing on the same launches (or one owner; no shared key was found).
- **The `0x65050a9b` router is public**: 18,855 token-moving transactions from 400+ signers in a day. This repo had filed it as the
  D65 crew's router; using it ties `0x5bc235ac` to nothing. A simulated call through it gives every caller the same output when pinned
  to one block (an earlier difference was the pool trading between calls).
- **`0x5bc235ac`'s October "funders"** (`0x01118901`, `0x05eade09`) are now among the keys that fire its buy contract: its own keys.

**Not checked (no archive state or explorer reachable):** where each wallet's ETH comes from, and whether any of them funds the
coins' creators. A sniper that launches coins from fresh wallets and buys them itself would pass the creator test above.
