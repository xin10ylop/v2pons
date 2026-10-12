// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// FlipRelayV3: buys and sells one token on a Uniswap V3 pool paired with WETH, from ETH it holds, on the owner's order, straight
/// through the pool (pool.swap and its callback: no router, no approval).
///
/// The pool is the factory's CREATE2 address for (WETH, token, fee), so only a pool built from Uniswap V3's own init code is traded
/// or paid. The buy wraps `amountIn` of this contract's ETH and keeps the tokens here. The sell sends every token this contract holds
/// into the pool, unwraps the WETH it gets and keeps the ETH here: it needs no balance query and no approval, so it can be signed at
/// the nonce after the buy before the buy's receipt exists. The pool being swapped, the token it is to be paid in and the most it may
/// be paid sit in storage for the length of the swap: the callback pays that pool only, only then, in that token and never more than
/// that; buy and sell refuse to start while a swap is in progress. The owner can pull back any ETH or token.
interface IUniswapV3Pool {
    function swap(address recipient, bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96, bytes calldata data)
        external returns (int256 amount0, int256 amount1);
}

interface IWETH {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
}

contract FlipRelayV3 {
    address public immutable owner;
    address public constant FACTORY = 0x1f7d7550B1b028f7571E69A784071F0205FD2EfA;                     // Uniswap V3's factory
    address public constant WETH = 0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73;
    bytes32 public constant POOL_INIT_CODE_HASH = 0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54;
    uint160 private constant MIN_SQRT_RATIO_LIMIT = 4295128740;                                        // TickMath.MIN_SQRT_RATIO + 1
    uint160 private constant MAX_SQRT_RATIO_LIMIT = 1461446703485210103287273052203988822378723970341;  // TickMath.MAX_SQRT_RATIO - 1

    // the swap in progress (all 0 otherwise): the pool (the callback's check and the guard), the token it is paid in, the most it may get
    address private swapping;
    address private payToken;
    uint256 private payMax;

    error NotOwner();
    error NotPool(address sender);
    error Busy();
    error TooLate(uint256 blockTime, uint256 deadline);
    error NoPool(address pool);
    error Insufficient(uint256 balance, uint256 needed);
    error NothingToSell(address token);
    error TooLittleOut(uint256 got, uint256 minOut);
    error Overpay(uint256 owed, uint256 max);
    error TransferFailed(address token);

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address owner_) {
        require(owner_ != address(0), "owner");
        owner = owner_;
    }

    receive() external payable {}

    /// `amountIn` of this contract's ETH, wrapped, into the pool; the tokens stay here. Reverts under `minOut` tokens received, or in
    /// a block whose clock second is after `deadline`. If the pool's price limit cuts the fill short, the WETH it did not take is
    /// unwrapped back to ETH.
    function buy(address token, uint24 fee, uint256 amountIn, uint256 minOut, uint256 deadline) external onlyOwner returns (uint256 out) {
        address pool = _start(token, fee, deadline, WETH, amountIn);
        if (address(this).balance < amountIn) revert Insufficient(address(this).balance, amountIn);
        IWETH(WETH).deposit{value: amountIn}();
        bool zeroForOne = WETH < token;                 // WETH in: token0 in when WETH is token0
        uint256 before = IERC20(token).balanceOf(address(this));
        (int256 a0, int256 a1) = IUniswapV3Pool(pool).swap(
            address(this), zeroForOne, int256(amountIn), zeroForOne ? MIN_SQRT_RATIO_LIMIT : MAX_SQRT_RATIO_LIMIT, "");
        _end();
        uint256 paid = uint256(zeroForOne ? a0 : a1);
        if (paid < amountIn) IWETH(WETH).withdraw(amountIn - paid);
        out = IERC20(token).balanceOf(address(this)) - before;
        if (out < minOut) revert TooLittleOut(out, minOut);
    }

    /// Every token of `token` this contract holds into the pool; the WETH received is unwrapped and the ETH stays here. Reverts under
    /// `minOut` wei, after `deadline`, or with no token to sell.
    function sell(address token, uint24 fee, uint256 minOut, uint256 deadline) external onlyOwner returns (uint256 out) {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal == 0 || bal > uint256(type(int256).max)) revert NothingToSell(token);
        address pool = _start(token, fee, deadline, token, bal);
        bool zeroForOne = token < WETH;                 // the token in: token0 in when the token is token0
        (int256 a0, int256 a1) = IUniswapV3Pool(pool).swap(
            address(this), zeroForOne, int256(bal), zeroForOne ? MIN_SQRT_RATIO_LIMIT : MAX_SQRT_RATIO_LIMIT, "");
        _end();
        out = uint256(-(zeroForOne ? a1 : a0));
        if (out < minOut) revert TooLittleOut(out, minOut);
        IWETH(WETH).withdraw(out);
    }

    /// The pool calls back here inside swap: pay it what it is owed (the positive delta) in the token recorded for this swap (WETH on
    /// a buy, the token on a sell), never more than the recorded maximum. Any caller but the pool of the swap in progress is refused,
    /// at any time; `data` is not read.
    function uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes calldata) external {
        if (msg.sender != swapping) revert NotPool(msg.sender);
        int256 owed = amount0Delta > 0 ? amount0Delta : amount1Delta;
        if (owed > 0) {
            uint256 max = payMax;
            if (uint256(owed) > max) revert Overpay(uint256(owed), max);
            payMax = max - uint256(owed);
            _pay(payToken, msg.sender, uint256(owed));
        }
    }

    /// ETH back to the owner (amount 0 = everything).
    function withdraw(uint256 amount) external onlyOwner {
        (bool s, ) = owner.call{value: amount == 0 ? address(this).balance : amount}("");
        require(s, "withdraw");
    }

    /// `amount` of any ERC20 here (WETH included) back to the owner; 0 = all of it.
    function sweep(address token, uint256 amount) external onlyOwner {
        _pay(token, owner, amount == 0 ? IERC20(token).balanceOf(address(this)) : amount);
    }

    /// The deadline and the guard, the pool of (WETH, token, fee) as the factory's CREATE2 gives it (Uniswap V3's PoolAddress) and its
    /// code; then the swap in progress recorded: the pool, the token it is to be paid in and the most it may be paid.
    function _start(address token, uint24 fee, uint256 deadline, address pays, uint256 max) private returns (address pool) {
        if (block.timestamp > deadline) revert TooLate(block.timestamp, deadline);
        if (swapping != address(0)) revert Busy();
        (address t0, address t1) = token < WETH ? (token, WETH) : (WETH, token);
        pool = address(uint160(uint256(keccak256(abi.encodePacked(hex"ff", FACTORY, keccak256(abi.encode(t0, t1, fee)), POOL_INIT_CODE_HASH)))));
        if (pool.code.length == 0) revert NoPool(pool);
        (swapping, payToken, payMax) = (pool, pays, max);
    }

    /// The swap is over: nothing recorded any more.
    function _end() private {
        (swapping, payToken, payMax) = (address(0), address(0), 0);
    }

    /// An ERC20 transfer that accepts tokens returning nothing and refuses a false or a revert.
    function _pay(address token, address to, uint256 amount) private {
        (bool s, bytes memory r) = token.call(abi.encodeWithSelector(0xa9059cbb, to, amount));
        if (!(s && (r.length == 0 || abi.decode(r, (bool))))) revert TransferFailed(token);
    }
}
