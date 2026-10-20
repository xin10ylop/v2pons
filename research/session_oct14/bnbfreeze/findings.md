# BNB "HMM / Thinking Cat" freeze (token 0x950e6818...19, chain 56)

## Finding
The token is a reactive, per-address honeypot. Our first live trade (25 BNB, first buyer, L+52) cannot be
sold because the launcher bakes an "operator" address into storage **slot 6** (0xbd418ce6... for the 2995-byte
template) and `_transfer` reverts with EMPTY data whenever the operator has given the SENDER an ODD allowance.
The operator armed it by sending a plain-looking `approve(ourWallet, 2^256-1)` to the token
(tx 0xc3177267..., selector 0x095ea7b3, 18 blocks after our buy). 2^256-1 is odd -> frozen. The crowd is
unmarked (allowance[op][x]=0, even) so they trade freely, keeping the pool looking healthy.

## Exact rule (both templates)
slot6 = operator address, set ONLY in the constructor (no runtime SSTORE to literal slot 6).
_transfer(from,to,amt): revert(empty) iff  (X==0) && ( allowance[slot6][from] & 1 == 1 )
  - X is an exemption flag (0 for an ordinary holder transfer).
  - allowance[slot6][from] is read via mapping slot 1: keccak(from . keccak(slot6 . 1)).
  - Only bit 0 matters (parity). Proven by state override: 0,2,4,...,2^256-2 PASS; 1,3,...,2^256-1 REVERT.
Opcodes:
  - 2995-byte template (codehash 0x5faca898..., control-flow-flattened): state 0x5ca4955a at
    0x04ce DUP8; 0x04cf ISZERO; 0x04d0 DUP4; 0x04d1 AND; 0x04d2 ISZERO; 0x04d3 JUMPI 0x04f8; else 0x04f5 REVERT.
  - 1365-byte template (codehash 0x18449a16..., clean Solidity): 0x02b8 PUSH1 6 SLOAD ... 0x02d7 KECCAK256
    0x02d9 SLOAD; 0x02da DUP1 0x02db DUP6 0x02dc ISZERO 0x02dd DUP2 0x02de AND 0x02df ISZERO 0x02e0 JUMPI; else 0x02e6 REVERT.
  BASEFEE/NUMBER/COINBASE/SELFBALANCE + STATICCALL to precompiles 0x02/0x04 in the path are decoys (junk).

## Marking tx (disguise)
operator 0xbd418ce6 -> token, approve(spender=0x8881...our wallet, amount=2^256-1). Stored allowance = MAX (odd).
Approval EVENT logged a DECOY amount 779315887607126688577176379609004218641311158219 (not MAX). Raw storage of
allowance[op][us] = 0xffff...ff. No admin function, no blacklist mapping in the ABI; the freeze hides inside a
standard-looking approve + a standard Approval event with a fake value.

## Does it expire?
No. The marker is plain storage, no block/timestamp/decay input. Override sim at block L+5,000,000 / year 2065
still reverts. Only the operator writing an even value (0/even) to allowance[op][victim] lifts it. Permanent -100%.

## Why BnbRoundTrip passed / what catches it
BnbRoundTrip.run does buy+approve+sell in ONE eth_call from a FRESH fabricated contract (HARNESS 0x00..b0b0b0b0),
which has allowance[op][HARNESS]=0 (even) -> sell leg passes, returns ~99.5% of stake. Two independent blind spots:
  (a) it simulates a different address than the real wallet;
  (b) the freeze is applied REACTIVELY by a separate operator tx AFTER the buy -- no pre-buy, single-tx, same-block
      simulation can observe a mark that does not exist yet. A two-block EOA sim would ALSO pass (the mark tx is not
      part of it). The only pre-buy defense is STATIC: this codehash family is the honeypot.

## Fix
- src/bnb_live.py line 65-66: BNB_TOKEN_CODEHASHES is an ALLOW-list holding exactly the two honeypot templates.
  Invert it -- both 0x5faca898... and 0x18449a16... must be DENIED/refused. An allow-list of these two hashes
  whitelists the trap.
- Pre-buy check must read slot 6; if it holds a nonzero "operator" address that _transfer trusts, refuse (static
  pattern: _transfer gating on the parity/low bit of allowance[slot6][from]).
- Holding guard (detection only, cannot beat the mark): each block read allowance[slot6][ourWallet]; if its low bit
  flips (or a real-wallet sell eth_call reverts empty) the position is already frozen -> alarm/halt.
