// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// The exit test for a Uniswap-V2 line (deploy/base_v2_sim.py): never deployed. An eth_call with a state override puts this code at an
/// address with ETH; `roundTrip` buys the token through the router with `stake` ETH, reads what it got, approves the router and sells all
/// of it back, and returns the tokens bought and the ETH the sell returned. A token that blocks sells reverts the sell (the whole call);
/// a token with a sell tax returns less ETH than the constant-product quote; a clean token returns the quote. Nothing here holds money.
interface IV2Router {
    function swapExactETHForTokensSupportingFeeOnTransferTokens(uint amountOutMin, address[] calldata path, address to, uint deadline) external payable;
    function swapExactTokensForETHSupportingFeeOnTransferTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external;
    function getAmountsOut(uint amountIn, address[] calldata path) external view returns (uint[] memory);
}
interface IERC20 {
    function balanceOf(address) external view returns (uint);
    function approve(address, uint) external returns (bool);
}

contract V2RoundTrip {
    receive() external payable {}

    /// buy with `stake` wei of this contract's ETH, then sell everything; `holdSell` false skips the sell (a buy-only probe)
    function roundTrip(address router, address weth, address token, uint stake, bool doSell)
        external returns (uint tokensBought, uint ethBack, uint quoteBack)
    {
        address[] memory buyPath = new address[](2); buyPath[0] = weth; buyPath[1] = token;
        uint before = IERC20(token).balanceOf(address(this));
        IV2Router(router).swapExactETHForTokensSupportingFeeOnTransferTokens{value: stake}(0, buyPath, address(this), block.timestamp + 60);
        tokensBought = IERC20(token).balanceOf(address(this)) - before;
        if (!doSell) return (tokensBought, 0, 0);
        address[] memory sellPath = new address[](2); sellPath[0] = token; sellPath[1] = weth;
        uint[] memory q = IV2Router(router).getAmountsOut(tokensBought, sellPath); quoteBack = q[1];
        require(IERC20(token).approve(router, tokensBought), "approve failed");
        uint ethBefore = address(this).balance;
        IV2Router(router).swapExactTokensForETHSupportingFeeOnTransferTokens(tokensBought, 0, sellPath, address(this), block.timestamp + 60);
        ethBack = address(this).balance - ethBefore;
    }
}
