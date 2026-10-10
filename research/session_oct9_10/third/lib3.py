import sys, time, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from chain import *
from eth_utils import keccak
def caddr(a, n):
    a = bytes.fromhex(a[2:])
    def eb(b): return b if (len(b) == 1 and b[0] < 0x80) else bytes([0x80 + len(b)]) + b
    nenc = b'\x80' if n == 0 else eb(n.to_bytes((n.bit_length() + 7) // 8, 'big'))
    p = eb(a) + nenc
    return '0x' + keccak(bytes([0xc0 + len(p)]) + p)[-20:].hex()
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
