// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;
/// Research only (never deployed): placed by eth_call state override at the relay's owner address, it calls the relay and measures the gas
/// each call uses inside the EVM (the transaction adds 21,000, its calldata and a small L1 component).
contract GasProbe {
    function probe(address to, bytes calldata data, uint256 gasCap) external returns (bool ok, uint256 used, bytes memory ret) {
        uint256 g = gasleft();
        (ok, ret) = to.call{gas: gasCap}(data);
        used = g - gasleft();
    }
    /// buy then sell through the relay, each measured; the buy's and the sell's return data
    function roundtrip(address relay, bytes calldata buyData, bytes calldata sellData, uint256 gasCap)
        external returns (bool okb, uint256 gb, bytes memory rb, bool oks, uint256 gs, bytes memory rs, uint256 ethAfterBuy, uint256 ethAfterSell) {
        uint256 g = gasleft();
        (okb, rb) = relay.call{gas: gasCap}(buyData);
        gb = g - gasleft(); ethAfterBuy = relay.balance;
        g = gasleft();
        (oks, rs) = relay.call{gas: gasCap}(sellData);
        gs = g - gasleft(); ethAfterSell = relay.balance;
    }
}
