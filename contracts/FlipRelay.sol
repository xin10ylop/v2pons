// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// FlipRelay: buys and sells one token on a Uniswap v4 pool paired with native ETH (currency0 = address(0)), from ETH it holds,
/// on the owner's order, straight through the PoolManager (unlock, swap, settle, take: no router, no approval).
///
/// The buy takes `amountIn` of this contract's ETH and keeps the tokens here. The sell sends every token this contract holds
/// back into the pool and keeps the ETH here. So the sell needs no balance query and no approval, and can be signed at the
/// nonce after the buy before the buy's receipt exists: the engine sends it a fixed number of blocks later. Both settle
/// exactly what the swap says is owed (a partial fill at the price limit never strands value in the PoolManager). The owner
/// can pull back any ETH or token.
interface IPoolManager {
    struct PoolKey { address currency0; address currency1; uint24 fee; int24 tickSpacing; address hooks; }
    struct SwapParams { bool zeroForOne; int256 amountSpecified; uint160 sqrtPriceLimitX96; }
    function unlock(bytes calldata data) external returns (bytes memory);
    function swap(PoolKey memory key, SwapParams memory params, bytes calldata hookData) external returns (int256 delta);
    function settle() external payable returns (uint256);
    function sync(address currency) external;
    function take(address currency, address to, uint256 amount) external;
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
}

contract FlipRelay {
    IPoolManager public immutable pm;
    address public immutable owner;
    uint160 private constant MIN_SQRT_PRICE_LIMIT = 4295128740;                                        // TickMath.MIN_SQRT_PRICE + 1
    uint160 private constant MAX_SQRT_PRICE_LIMIT = 1461446703485210103287273052203988822378723970341;  // TickMath.MAX_SQRT_PRICE - 1

    error NotOwner();
    error NotPoolManager(address sender);
    error NotEthPair(address currency0);
    error TooLate(uint256 blockTime, uint256 deadline);
    error Insufficient(uint256 balance, uint256 needed);
    error TooLittleOut(uint256 got, uint256 minOut);
    error NothingToSell(address token);
    error TransferFailed(address token);

    constructor(address poolManager) {
        pm = IPoolManager(poolManager);
        owner = msg.sender;
    }

    receive() external payable {}

    /// `amountIn` of this contract's ETH into the pool; the tokens stay here. Reverts under `minOut` tokens, or in a block whose
    /// clock second is after `deadline` (0 = no deadline).
    function buy(IPoolManager.PoolKey calldata key, uint256 amountIn, uint256 minOut, uint256 deadline) external returns (uint256 out) {
        if (msg.sender != owner) revert NotOwner();
        if (deadline != 0 && block.timestamp > deadline) revert TooLate(block.timestamp, deadline);
        if (key.currency0 != address(0)) revert NotEthPair(key.currency0);
        if (address(this).balance < amountIn) revert Insufficient(address(this).balance, amountIn);
        out = abi.decode(pm.unlock(abi.encode(true, key, amountIn, minOut)), (uint256));
    }

    /// Every token of `key.currency1` this contract holds into the pool; the ETH stays here. Reverts under `minOut` wei.
    function sell(IPoolManager.PoolKey calldata key, uint256 minOut, uint256 deadline) external returns (uint256 out) {
        if (msg.sender != owner) revert NotOwner();
        if (deadline != 0 && block.timestamp > deadline) revert TooLate(block.timestamp, deadline);
        if (key.currency0 != address(0)) revert NotEthPair(key.currency0);
        uint256 bal = IERC20(key.currency1).balanceOf(address(this));
        if (bal == 0) revert NothingToSell(key.currency1);
        out = abi.decode(pm.unlock(abi.encode(false, key, bal, minOut)), (uint256));
    }

    /// The PoolManager calls back here inside unlock: one exact-input swap, then settle what is owed and take what is due.
    function unlockCallback(bytes calldata data) external returns (bytes memory) {
        if (msg.sender != address(pm)) revert NotPoolManager(msg.sender);
        (bool isBuy, IPoolManager.PoolKey memory key, uint256 amountIn, uint256 minOut) = abi.decode(data, (bool, IPoolManager.PoolKey, uint256, uint256));
        int256 delta = pm.swap(key, IPoolManager.SwapParams(isBuy, -int256(amountIn), isBuy ? MIN_SQRT_PRICE_LIMIT : MAX_SQRT_PRICE_LIMIT), "");
        int256 d0; int256 d1;                           // BalanceDelta: amount0 in the high 128 bits, amount1 in the low 128 (both signed)
        assembly {
            d0 := sar(128, delta)
            d1 := signextend(15, delta)
        }
        uint256 out;
        if (isBuy) {                                    // we owe ETH (d0 < 0), the pool owes tokens (d1 > 0)
            if (d0 > 0 || d1 < 0) revert TooLittleOut(0, minOut);
            out = uint256(d1);
            if (out < minOut) revert TooLittleOut(out, minOut);
            pm.settle{value: uint256(-d0)}();
            if (out > 0) pm.take(key.currency1, address(this), out);
        } else {                                        // we owe tokens (d1 < 0), the pool owes ETH (d0 > 0)
            if (d1 > 0 || d0 < 0) revert TooLittleOut(0, minOut);
            out = uint256(d0);
            if (out < minOut) revert TooLittleOut(out, minOut);
            uint256 owed = uint256(-d1);
            if (owed > 0) {
                pm.sync(key.currency1);
                (bool s, bytes memory r) = key.currency1.call(abi.encodeWithSelector(0xa9059cbb, address(pm), owed));
                if (!(s && (r.length == 0 || abi.decode(r, (bool))))) revert TransferFailed(key.currency1);
                pm.settle();
            }
            if (out > 0) pm.take(address(0), address(this), out);
        }
        return abi.encode(out);
    }

    /// ETH back to the owner (amount 0 = everything).
    function withdraw(uint256 amount) external {
        if (msg.sender != owner) revert NotOwner();
        (bool s, ) = owner.call{value: amount == 0 ? address(this).balance : amount}("");
        require(s, "withdraw");
    }

    /// Any ERC20 that ended up here, back to the owner.
    function sweep(address token) external {
        if (msg.sender != owner) revert NotOwner();
        uint256 bal = IERC20(token).balanceOf(address(this));
        (bool s, bytes memory r) = token.call(abi.encodeWithSelector(0xa9059cbb, owner, bal));
        require(s && (r.length == 0 || abi.decode(r, (bool))), "sweep");
    }
}
