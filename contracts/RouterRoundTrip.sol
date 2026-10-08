// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// Test only, never deployed: placed at an address by eth_call state override with some ETH, it sends the engine's exact buy
/// calldata to the Universal Router, reads the tokens it got, makes the fleet's two approvals (token -> Permit2, Permit2 ->
/// router) and sends the engine's exact sell calldata with the token amount patched in at the engine's AMOUNT_IN_OFFSET, so a
/// router round trip is checked on the real router, Permit2 and PoolManager with no transaction. Returns what each leg produced.
interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
}

interface IPermit2 {
    function approve(address token, address spender, uint160 amount, uint48 expiration) external;
}

contract RouterRoundTrip {
    receive() external payable {}

    function run(address router, address permit2, address token, bytes calldata buyData, uint256 buyValue, bytes calldata sellData, uint256 amountInOffset)
        external returns (uint256 tokensOut, uint256 ethBack, uint256 gasBuy, uint256 gasSell)
    {
        gasBuy = _call(router, buyValue, buyData, "buy: ");
        tokensOut = IERC20(token).balanceOf(address(this));
        require(tokensOut > 0, "no tokens");
        IERC20(token).approve(permit2, type(uint256).max);
        IPermit2(permit2).approve(token, router, type(uint160).max, type(uint48).max);
        bytes memory sd = _patched(sellData, amountInOffset, tokensOut);
        uint256 eth0 = address(this).balance;
        gasSell = _call(router, 0, sd, "sell: ");
        ethBack = address(this).balance - eth0;
        require(IERC20(token).balanceOf(address(this)) == 0, "tokens left");
    }

    function _call(address to, uint256 value, bytes memory data, string memory leg) internal returns (uint256 gasUsed) {
        uint256 g0 = gasleft();
        (bool ok, bytes memory ret) = to.call{value: value}(data);
        gasUsed = g0 - gasleft();
        if (!ok) revert(string(abi.encodePacked(leg, _hex(ret))));
    }

    function _patched(bytes calldata data, uint256 offset, uint256 amount) internal pure returns (bytes memory sd) {
        sd = data;
        assembly { mstore(add(add(sd, 32), offset), amount) }
    }

    function _hex(bytes memory b) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        uint256 n = b.length > 36 ? 36 : b.length;
        bytes memory s = new bytes(2 * n);
        for (uint256 i = 0; i < n; i++) {
            s[2 * i] = alphabet[uint8(b[i]) >> 4];
            s[2 * i + 1] = alphabet[uint8(b[i]) & 0x0f];
        }
        return string(s);
    }
}
