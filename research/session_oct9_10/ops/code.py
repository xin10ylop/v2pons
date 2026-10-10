import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
a = sys.argv[1]
c = rpc("eth_getCode", [a, "latest"])
open(f"code_{a[:10]}.hex", "w").write(c)
from eth_utils import keccak
print(a, "len", (len(c)-2)//2, "hash", keccak(hexstr=c).hex())
