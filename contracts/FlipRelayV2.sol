// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// FlipRelayV2: the owner's relay for a Uniswap-V2 line (docs/BASE_V2.md). It holds the stake in ETH, buys a token through the V2 router with
/// `buy` and sells everything it holds with `sell`, both owner-only, each a single transaction (the sell approves inside the call, so no
/// separate approval transaction stands between our buy and our exit). `withdraw` returns ETH, `sweep` any token. The router and WETH are
/// immutable; a path is always [WETH, token] or [token, WETH]. minOut is enforced by the router (the "SupportingFeeOnTransferTokens"
/// variants check the balance delta, so a token that pays out less than minOut reverts the whole call).
interface IV2Router {
    function swapExactETHForTokensSupportingFeeOnTransferTokens(uint amountOutMin, address[] calldata path, address to, uint deadline) external payable;
    function swapExactTokensForETHSupportingFeeOnTransferTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external;
}
interface IERC20 {
    function balanceOf(address) external view returns (uint);
    function approve(address, uint) external returns (bool);
    function transfer(address, uint) external returns (bool);
}

contract FlipRelayV2 {
    address public immutable owner;
    address public immutable router;
    address public immutable weth;

    error NotOwner();
    error NoStake();
    error NothingToSell();

    constructor(address router_, address weth_) { owner = msg.sender; router = router_; weth = weth_; }
    receive() external payable {}
    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }

    /// buy `token` with `stake` wei of the relay's ETH; the router reverts under `minOut`
    function buy(address token, uint stake, uint minOut, uint deadline) external onlyOwner returns (uint tokens) {
        if (address(this).balance < stake) revert NoStake();
        address[] memory path = new address[](2); path[0] = weth; path[1] = token;
        uint before = IERC20(token).balanceOf(address(this));
        IV2Router(router).swapExactETHForTokensSupportingFeeOnTransferTokens{value: stake}(minOut, path, address(this), deadline);
        tokens = IERC20(token).balanceOf(address(this)) - before;
    }

    /// sell every unit of `token` the relay holds; the router reverts under `minOut`
    function sell(address token, uint minOut, uint deadline) external onlyOwner returns (uint ethOut) {
        uint amount = IERC20(token).balanceOf(address(this));
        if (amount == 0) revert NothingToSell();
        IERC20(token).approve(router, amount);
        address[] memory path = new address[](2); path[0] = token; path[1] = weth;
        uint before = address(this).balance;
        IV2Router(router).swapExactTokensForETHSupportingFeeOnTransferTokens(amount, minOut, path, address(this), deadline);
        ethOut = address(this).balance - before;
    }

    function withdraw(uint amount) external onlyOwner { (bool ok, ) = owner.call{value: amount == 0 ? address(this).balance : amount}(""); require(ok, "withdraw failed"); }
    function sweep(address token) external onlyOwner { IERC20(token).transfer(owner, IERC20(token).balanceOf(address(this))); }
}
