// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;
/// deploy/base_v2_relay_sim.py's harness, never deployed: as the relay's owner it buys and sells through FlipRelayV2 in one call.
interface IFlipRelayV2 {
    function buy(address token, uint stake, uint minOut, uint deadline) external returns (uint);
    function sell(address token, uint minOut, uint deadline) external returns (uint);
}
contract V2RelayHarness {
    receive() external payable {}
    function run(address relay, address token, uint stake, uint sellMinOut) external returns (uint tokens, uint ethOut) {
        tokens = IFlipRelayV2(relay).buy(token, stake, 0, block.timestamp + 60);
        ethOut = IFlipRelayV2(relay).sell(token, sellMinOut, block.timestamp + 60);
    }
}
