// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// SellCheckV3: never deployed. The engine (src/flip_engine.py, V3_SELL_CHECK; docs/HANDOFF.md 16.22) places this code at WALLET's
/// address (the V3 relay's owner) by an eth_call state override and calls check(): one buy of `amountIn` through RELAY_V3 on a live
/// pool, then the sell of everything it got, on the latest state, nothing sent. A token that lets the relay buy but not sell (a sell
/// lock: it refuses an outsider's transfer into the pool) reverts the sell, and with it this call; so does a pool that gives no token.
/// Compiled with solc 0.8.26 (standard JSON, source key "SellCheckV3.sol"), optimizer on (200 runs), EVM cancun: its runtime code is
/// SELL_CHECK_CODE in the engine (test 20p recompiles it when solcx is installed).
interface IRelayV3 {
    function buy(address token, uint24 fee, uint256 amountIn, uint256 minOut, uint256 deadline) external returns (uint256);
    function sell(address token, uint24 fee, uint256 minOut, uint256 deadline) external returns (uint256);
}

contract SellCheckV3 {
    /// the tokens the buy got (at least 1, its minOut) and the ETH the sell of all of them got back
    function check(address relay, address token, uint24 fee, uint256 amountIn, uint256 deadline) external returns (uint256 got, uint256 back) {
        got = IRelayV3(relay).buy(token, fee, amountIn, 1, deadline);
        back = IRelayV3(relay).sell(token, fee, 0, deadline);
    }
}
