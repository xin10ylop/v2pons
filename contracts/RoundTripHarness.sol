// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// Test only, never deployed: placed at an address by eth_call state override as the relay's owner, it runs one buy and one
/// sell through the relay on a live pool and returns what each leg produced, so a relay build is checked on the real
/// PoolManager with no transaction.
interface IRelay {
    struct PoolKey { address currency0; address currency1; uint24 fee; int24 tickSpacing; address hooks; }
    function buy(PoolKey calldata key, uint256 amountIn, uint256 minOut, uint256 deadline) external returns (uint256);
    function sell(PoolKey calldata key, uint256 minOut, uint256 deadline) external returns (uint256);
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
}

contract RoundTripHarness {
    function run(address relay, IRelay.PoolKey calldata key, uint256 amountIn, uint256 minOutBuy)
        external returns (uint256 tokensOut, uint256 tokensHeld, uint256 ethBack, uint256 ethHeldAfter)
    {
        uint256 eth0 = relay.balance;
        tokensOut = IRelay(relay).buy(key, amountIn, minOutBuy, 0);
        tokensHeld = IERC20(key.currency1).balanceOf(relay);
        ethBack = IRelay(relay).sell(key, 0, 0);
        ethHeldAfter = relay.balance;
        require(eth0 - amountIn + ethBack == ethHeldAfter, "eth accounting");
        require(IERC20(key.currency1).balanceOf(relay) == 0, "tokens left");
    }
}
