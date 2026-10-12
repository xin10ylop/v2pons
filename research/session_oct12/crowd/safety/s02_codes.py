"""The tokens' runtime code (eth_getCode at the head): its keccak (the code hash), size, and skeleton (opcodes without push data, the CBOR
metadata stripped: a hash that ignores constants such as name/symbol baked in as immutables). Grouped by template; for each template, one
token's dispatcher selectors (PUSH4 x / EQ), the opcodes that could implement a tax, a lock or an owner power (CALL, DELEGATECALL,
STATICCALL, CALLCODE, SELFDESTRUCT, ORIGIN, TIMESTAMP, NUMBER, GASPRICE, COINBASE, BALANCE, CREATE/CREATE2), the number of SSTOREs and
SLOADs, and its ASCII strings. Writes s02_codes.json (per token: hash, size, skeleton) and s02_codes.out."""
from common import *
import rpc, collections
L = json.load(open(J("s01_launches.json")))["launches"]
toks = [x["token"] for x in L]
C = J("s02_code_cache.jsonl"); have = {r["token"]: r["code"] for r in jl(C)}
todo = [t for t in toks if t not in have]
with open(C, "a") as f:
    for i in range(0, len(todo), 20):
        ch = todo[i:i + 20]
        for t, c in zip(ch, rpc.batch("eth_getCode", [[t, "latest"] for t in ch])):
            have[t] = c; f.write(json.dumps({"token": t, "code": c}) + "\n")
def strip(b):
    n = int.from_bytes(b[-2:], "big")
    return b[:-n - 2] if n + 2 < len(b) and b[-n - 2] in (0xa1, 0xa2) else b
def dis(b):
    i = 0; out = []
    while i < len(b):
        op = b[i]; n = op - 0x5f if 0x60 <= op <= 0x7f else 0; out.append((i, op, b[i + 1:i + 1 + n])); i += 1 + n
    return out
NAMES = {0xf1: "CALL", 0xf4: "DELEGATECALL", 0xfa: "STATICCALL", 0xf2: "CALLCODE", 0xff: "SELFDESTRUCT", 0x32: "ORIGIN", 0x42: "TIMESTAMP", 0x43: "NUMBER",
         0x3a: "GASPRICE", 0x41: "COINBASE", 0x31: "BALANCE", 0xf0: "CREATE", 0xf5: "CREATE2", 0x55: "SSTORE", 0x54: "SLOAD", 0x33: "CALLER", 0x30: "ADDRESS", 0xa0: "LOG0",
         0xa1: "LOG1", 0xa2: "LOG2", 0xa3: "LOG3", 0xa4: "LOG4", 0x3b: "EXTCODESIZE", 0x3f: "EXTCODEHASH", 0x48: "BASEFEE", 0x5c: "TLOAD", 0x5d: "TSTORE"}
def code_end(ins):
    """the end of the executable part: data (strings, the metadata) usually follows the last INVALID 0xfe after the last JUMP/STOP/RETURN"""
    fe = [i for i, op, _ in ins if op == 0xfe]
    return fe[0] if fe else (ins[-1][0] + 1 if ins else 0)
rows = []; tm = collections.defaultdict(list)
for x in L:
    c = have[x["token"]]; b = bytes.fromhex(c[2:]); core = strip(b); ins = dis(core)
    sk = keccak(bytes(op for _, op, _ in ins)).hex()[:16]; h = keccak(b).hex()
    rows.append({"token": x["token"], "pool": x["pool"], "lb": x["lb"], "ts": x["ts"], "qs": x["qs"], "codehash": "0x" + h, "size": len(b), "skel": sk})
    tm[(len(b), sk)].append(x)
json.dump(rows, open(J("s02_codes.json"), "w"))
print(f"tokens {len(rows)}; code hashes distinct {len(set(r['codehash'] for r in rows))}; templates (size, skeleton) {len(tm)}")
for (size, sk), v in sorted(tm.items(), key=lambda kv: -len(kv[1])):
    hs = collections.Counter(r["codehash"] for r in rows if (r["size"], r["skel"]) == (size, sk))
    print(f"\n== template size {size} skel {sk}: {len(v)} tokens, {len(hs)} code hashes (top {[(h[:12], n) for h, n in hs.most_common(3)]}); "
          f"first {utc(min(x['ts'] for x in v))} last {utc(max(x['ts'] for x in v))}; WETH token1 {sum(x['qs'] for x in v)}")
    x = v[-1]; b = bytes.fromhex(have[x["token"]][2:]); core = strip(b); ins = dis(core); end = code_end(ins)
    ex = [(i, op, a) for i, op, a in ins if i < end]
    sels = sorted({a.hex() for k, (i, op, a) in enumerate(ex) if op == 0x63 and k + 1 < len(ex) and ex[k + 1][1] == 0x14 or (op == 0x63 and k + 2 < len(ex) and ex[k + 2][1] == 0x14)})
    cnt = collections.Counter(NAMES[op] for i, op, a in ex if op in NAMES)
    print(f"   example {x['token']} (pool {x['pool']}, launch {utc(x['ts'])}); executable part {end} of {len(core)} bytes (metadata {len(b) - len(core)})")
    print(f"   selectors ({len(sels)}): {' '.join(sels)}")
    print(f"   opcodes: {dict(sorted(cnt.items()))}")
    strs = []; cur = b""
    for byte in core[end:] + b"\x00":
        if 32 <= byte < 127: cur += bytes([byte])
        else:
            if len(cur) >= 6: strs.append(cur.decode())
            cur = b""
    for i, op, a in ex:                                                        # strings pushed as constants (PUSH32 revert reasons)
        if op >= 0x70 and sum(32 <= c < 127 for c in a) >= len(a) * 0.8 and len(a) >= 8: strs.append(a.rstrip(b"\x00").decode(errors="replace"))
    print(f"   strings: {strs[:30]}")
    if len(hs) > 1:                                                            # what differs between two tokens of one template (the constants)
        a0, a1 = [r["token"] for r in rows if (r["size"], r["skel"]) == (size, sk)][:2]
        b0, b1 = bytes.fromhex(have[a0][2:]), bytes.fromhex(have[a1][2:])
        diff = [i for i in range(min(len(b0), len(b1))) if b0[i] != b1[i]]
        runs = []
        for i in diff:
            if runs and i <= runs[-1][1] + 4: runs[-1][1] = i
            else: runs.append([i, i])
        print(f"   two of its tokens differ at {len(diff)} bytes in {len(runs)} runs: {[(a, b - a + 1) for a, b in runs[:12]]}")
print(rpc.STATS)
