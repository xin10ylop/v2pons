// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// Test only, never deployed: placed at an address by eth_call state override as the V3 relay's owner, it runs one buy and one sell
/// through the relay on a live Uniswap V3 pool, with QuoterV2's quote of each leg taken on the same state just before it, and returns
/// what each leg produced, so a relay build is checked on the real pools with no transaction.
interface IRelayV3 {
    function buy(address token, uint24 fee, uint256 amountIn, uint256 minOut, uint256 deadline) external returns (uint256);
    function sell(address token, uint24 fee, uint256 minOut, uint256 deadline) external returns (uint256);
    function WETH() external view returns (address);
}

interface IQuoterV2 {
    struct QuoteExactInputSingleParams { address tokenIn; address tokenOut; uint256 amountIn; uint24 fee; uint160 sqrtPriceLimitX96; }
    function quoteExactInputSingle(QuoteExactInputSingleParams memory params)
        external returns (uint256 amountOut, uint160 sqrtPriceX96After, uint32 initializedTicksCrossed, uint256 gasEstimate);
}

interface IPool {
    function slot0() external view returns (uint160 sqrtPriceX96, int24 tick, uint16, uint16, uint16, uint8, bool);
    function liquidity() external view returns (uint128);
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
}

contract RoundTripHarnessV3 {
    struct Args { address relay; address quoter; address pool; address token; uint24 fee; uint256 amountIn; uint256 minOutBuy; uint256 minOutSell; uint256 deadline; }

    /// r: [0] sqrtP before the buy, [1] liquidity before, [2] QuoterV2's buy quote, [3] its initialized ticks crossed, [4] the buy's
    /// tokens out, [5] the relay's token balance after it, [6] sqrtP after the buy, [7] liquidity after, [8] QuoterV2's quote for
    /// selling that balance, [9] its ticks crossed, [10] the sell's ETH out, [11] the relay's ETH after, [12] gas of the buy call,
    /// [13] gas of the sell call, [14] sqrtP after the sell
    function run(Args calldata a) external returns (uint256[15] memory r) {
        address weth = IRelayV3(a.relay).WETH();
        uint256 eth0 = a.relay.balance;
        (r[0], r[1]) = _state(a.pool);
        (r[2], r[3]) = _quote(a.quoter, weth, a.token, a.amountIn, a.fee);
        uint256 g = gasleft();
        r[4] = IRelayV3(a.relay).buy(a.token, a.fee, a.amountIn, a.minOutBuy, a.deadline);
        r[12] = g - gasleft();
        r[5] = IERC20(a.token).balanceOf(a.relay);
        require(a.relay.balance == eth0 - a.amountIn, "buy: eth accounting (a partial fill?)");
        require(IERC20(weth).balanceOf(a.relay) == 0, "buy: weth left");
        (r[6], r[7]) = _state(a.pool);
        (r[8], r[9]) = _quote(a.quoter, a.token, weth, r[5], a.fee);
        g = gasleft();
        r[10] = IRelayV3(a.relay).sell(a.token, a.fee, a.minOutSell, a.deadline);
        r[13] = g - gasleft();
        r[11] = a.relay.balance;
        (r[14], ) = _state(a.pool);
        require(r[11] == eth0 - a.amountIn + r[10], "sell: eth accounting");
        require(IERC20(a.token).balanceOf(a.relay) == 0, "sell: tokens left");
        require(IERC20(weth).balanceOf(a.relay) == 0, "sell: weth left");
    }

    /// A buy alone (for a pool with no liquidity left, where the fill is cut short): [0] tokens out, [1] the relay's ETH before,
    /// [2] after, [3] the relay's WETH after, [4] gas of the buy call.
    function buyOnly(address relay, address token, uint24 fee, uint256 amountIn, uint256 minOut, uint256 deadline) external returns (uint256[5] memory r) {
        r[1] = relay.balance;
        uint256 g = gasleft();
        r[0] = IRelayV3(relay).buy(token, fee, amountIn, minOut, deadline);
        r[4] = g - gasleft();
        r[2] = relay.balance;
        r[3] = IERC20(IRelayV3(relay).WETH()).balanceOf(relay);
    }

    function _state(address pool) private view returns (uint256 sqrtP, uint256 liq) {
        (uint160 s, , , , , , ) = IPool(pool).slot0();
        return (s, IPool(pool).liquidity());
    }

    function _quote(address quoter, address tokenIn, address tokenOut, uint256 amountIn, uint24 fee) private returns (uint256 out, uint256 crossed) {
        (uint256 q, , uint32 x, ) = IQuoterV2(quoter).quoteExactInputSingle(IQuoterV2.QuoteExactInputSingleParams(tokenIn, tokenOut, amountIn, fee, 0));
        return (q, x);
    }
}
