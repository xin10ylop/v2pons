// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
interface IERC20 { function transfer(address, uint256) external returns (bool); function balanceOf(address) external view returns (uint256);
                   function transferFrom(address, address, uint256) external returns (bool); function approve(address, uint256) external returns (bool); }
/// Research only (never deployed): placed by eth_call state override at an address that holds tokens (its balance set by override), it moves
/// `amt` to `to` and reports what left it and what arrived (a transfer tax or a burn on transfer shows as a difference), then approves a
/// second probe address and has nothing else to do.
contract TaxProbe {
    function run(address token, address to, uint256 amt) external returns (uint256 left, uint256 arrived, bool ok) {
        uint256 a0 = IERC20(token).balanceOf(address(this)); uint256 b0 = IERC20(token).balanceOf(to);
        ok = IERC20(token).transfer(to, amt);
        left = a0 - IERC20(token).balanceOf(address(this)); arrived = IERC20(token).balanceOf(to) - b0;
    }
}
