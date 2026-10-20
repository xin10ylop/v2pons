"""The 2.433 operator's Base launch mechanics (the 09:42 UTC Oct 14 test, launch block 52590807, and the 09:32 one, 52590492): every
transaction from L to L+32 that touches the launcher, the hook, the token, the operator's wallets or the bot's buy contract 0x987d5db8,
with its calldata words; the bot buy's arguments (to find its minOut and so its price tolerance) against the pool's output at that point.
Tenderly's public Base gateway (old blocks), read-only."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.25
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
buyers = {a.lower() for a, n, b in json.load(open(SRC + "c16_rh_wallets_xchain.json"))["buyers_bsc"]}
CASES = {52590807: {"launcher": "0xd93bef10148cce1c7d462ea65d2482a8cca50bab", "token": "0x3a73002fcad288a2ce1aff82fad49229b060a777",
                    "hook": "0x1c888901220490eb5a1dc0a0e8ee106616c28080", "wallet": "0x72d0cac5017dd7e2bcf3cfbde9079eae796c163c"},
         52590492: {"launcher": "0x32ab7e9886af345a53d412401307fabcc55bfee0", "token": "0xbe07c8c3cadd6f601684ef708573215d230ea777",
                    "hook": "0x0a37fce6d240d416bc5955173c9a6c1af586c080", "wallet": "0x4d40df2e5fb79b8b4cfc03ca9451a3462e813084"}}
BOT = "0x987d5db84d105c1f49391af409cc34c6050fb1d0"
for L, c in CASES.items():
    print(f"=== launch {L}")
    watch = {c["launcher"], c["token"], c["hook"], c["wallet"], BOT}
    for b in range(L, L + 33):
        B = xr.batch("base_t", "eth_getBlockByNumber", [[hex(b), True]], n=1)[0]
        for i, t in enumerate(B["transactions"]):
            f = t["from"].lower(); to = (t.get("to") or "").lower(); inp = t["input"]
            if f in watch or to in watch or f in buyers or c["token"][2:] in inp.lower():
                who = "WALLET" if f == c["wallet"] else ("buyer" if f in buyers else f[:10])
                words = [inp[10 + 64 * k: 74 + 64 * k] for k in range((len(inp) - 10) // 64)]
                print(f"  +{b - L:<2} idx {i:<3} {who} -> {to[:10]} {inp[:10]} {(len(inp) - 2) // 2} B val {int(t['value'], 16) / 1e18:.6f} "
                      f"gas {int(t['gas'], 16)} prio {int(t.get('maxPriorityFeePerGas', '0x0'), 16) / 1e9:.4f} gwei max {int(t.get('maxFeePerGas', t.get('gasPrice', '0x0')), 16) / 1e9:.4f}")
                if to == BOT or (f == c["wallet"] and b > L):
                    print("       words:", [w.lstrip("0") or "0" for w in words][:12])
