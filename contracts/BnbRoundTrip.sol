// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// Never deployed. src/bnb_live.py places this code by eth_call state override (code and a balance) at a fresh address and calls
/// run() from the wallet: one buy and one sell of a live PancakeSwap V2 pool through the router, with the same calls the wallet makes
/// (the fee-on-transfer-supporting swaps and an approve of the whole amount), and returns what each leg produced and the gas each used.
/// The engine refuses a pool whose token cannot be sold back, or sells back for less than 90% of the stake (a honeypot, a transfer tax,
/// a blacklist), before it buys. Nothing here can move money: an eth_call is never a transaction.
interface IRouter02 {
    function swapExactETHForTokensSupportingFeeOnTransferTokens(uint256 amountOutMin, address[] calldata path, address to, uint256 deadline)
        external payable;
    function swapExactTokensForETHSupportingFeeOnTransferTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to,
        uint256 deadline) external;
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
}

contract BnbRoundTrip {
    /// stage: 0 the round trip ran; 1 the buy reverted; 2 the approve reverted or returned false; 3 the sell reverted.
    /// tokensGot: the harness's token balance gained by the buy (after any transfer tax); bnbBack: its BNB gained by the sell.
    function run(address router, address wbnb, address token, uint256 stake)
        external
        returns (uint256 stage, uint256 tokensGot, uint256 bnbBack, uint256 gasBuy, uint256 gasApprove, uint256 gasSell)
    {
        address[] memory path = new address[](2);
        path[0] = wbnb;
        path[1] = token;
        uint256 t0 = IERC20(token).balanceOf(address(this));
        uint256 g = gasleft();
        try IRouter02(router).swapExactETHForTokensSupportingFeeOnTransferTokens{value: stake}(0, path, address(this), block.timestamp) {}
        catch {
            return (1, 0, 0, 0, 0, 0);
        }
        gasBuy = g - gasleft();
        tokensGot = IERC20(token).balanceOf(address(this)) - t0;
        g = gasleft();
        try IERC20(token).approve(router, type(uint256).max) returns (bool ok) {
            if (!ok) return (2, tokensGot, 0, gasBuy, 0, 0);
        } catch {
            return (2, tokensGot, 0, gasBuy, 0, 0);
        }
        gasApprove = g - gasleft();
        path[0] = token;
        path[1] = wbnb;
        uint256 b0 = address(this).balance;
        g = gasleft();
        try IRouter02(router).swapExactTokensForETHSupportingFeeOnTransferTokens(tokensGot, 0, path, address(this), block.timestamp) {}
        catch {
            return (3, tokensGot, 0, gasBuy, gasApprove, 0);
        }
        gasSell = g - gasleft();
        bnbBack = address(this).balance - b0;
    }

    receive() external payable {}
}
