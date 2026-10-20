"""Verify launcher creation tx + funding hops (by tx hash), deployer-chain nonces at latest, and code hashes of the launcher and sample copies."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch, rpc
from eth_utils import keccak
TX = {"deploy": "0x7022ad9304f44da91edab20de0e17b9d30cd11810c3e7e5896e854ed50e71789", "first_launch": "0x5abcd10225ed4e8e27a8057a7d3d3b95f2892321b9b6d62ac3b292211d97c3f9",
      "fund_3b11": "0x69653e38ecd216b4eb8f9ca72169d79831c39de3ae6ed5ecea22e29684bb0120", "fund_3130": "0x1313e56fc0349699d639846e54a1967848c06866e9a1a0f11596d48fb7adc364",
      "fund_5ec3": "0xd82fa12693753e17d62a00aa0aa99c81beeb8e9e6414d9ad9e891d7c41e66550"}
r = batch([("eth_getTransactionByHash", [h]) for h in TX.values()] + [("eth_getTransactionReceipt", [TX["deploy"]])])
for (k, h), t in zip(TX.items(), r[:-1]):
    print(k, h[:12], "blk", int(t["blockNumber"], 16), t["from"], "->", t["to"], int(t["value"], 16) / 1e18, "ETH nonce", int(t["nonce"], 16), "type", t.get("type"),
          "gas", int(t["gas"], 16), "tip", int(t.get("maxPriorityFeePerGas", "0x0"), 16) / 1e9, "gwei, input bytes", (len(t["input"]) - 2) // 2)
dep = r[0]; rc = r[-1]
print("deploy receipt: status", rc["status"], "contractAddress", rc["contractAddress"], "gasUsed", int(rc["gasUsed"], 16), "logs", len(rc["logs"]))
inp = dep["input"]; tail = inp[-192:]
print("constructor args (last 3 words):", ["0x" + tail[i*64+24:(i+1)*64] for i in range(3)])
blk = rpc("eth_getBlockByNumber", [dep["blockNumber"], False]); import time
print("deploy time UTC", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))))
A = ["0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5", "0x3130ea49fdcaaddeb59078b233ca55b705e23f3f", "0x5ec3c42876cfdfe266081df7ffd587cde11edc85", "0xcb88b74cb295eb8b501ca3a4103e35c74e545599"]
n = batch([("eth_getTransactionCount", [a, "latest"]) for a in A] + [("eth_getBalance", [a, "latest"]) for a in A])
for i, a in enumerate(A): print("latest nonce", a, int(n[i], 16), "balance", int(n[i + 4], 16) / 1e18)
C = ["0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0xd1cc99aa33b6cfc5246d8f7c4fc4492c367425bc", "0x00344844739b38678e30f47405cbd19ff001f52a", "0x816d73e4f67b671d376973975da0afca1d738d78"]
o = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/other_launcher_logs.json"))
step = max(1, len(o) // 24); C += [o[i]["address"].lower() for i in range(0, len(o), step)]
codes = batch([("eth_getCode", [c, "latest"]) for c in C])
import collections; hs = collections.Counter()
for c, code in zip(C, codes):
    h = keccak(hexstr=code).hex()[:8] if code and code != "0x" else "EMPTY"; hs[h] += 1
    if c in C[:4]: print("code", c, (len(code) - 2) // 2, "bytes, hash", h)
print("code hashes over", len(C), "addresses (launcher + 3 named copies + every %d-th copy):" % step, dict(hs))
