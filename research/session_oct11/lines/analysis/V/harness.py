"""A minimal sequential-call harness in raw EVM bytecode (no compiler on this box), for eth_call with a state override.
calldata = records [target:32][len:32][data, padded to 32]; it CALLs each target in order with value 0 and returns the first word of each
call's return data (32 bytes per call). If a call fails it reverts with [index of the failed call:32][that call's revert data]."""
OP = {"STOP": 0x00, "ADD": 0x01, "MUL": 0x02, "GT": 0x11, "ISZERO": 0x15, "AND": 0x16, "NOT": 0x19, "POP": 0x50, "MSTORE": 0x52, "JUMP": 0x56, "JUMPI": 0x57,
      "JUMPDEST": 0x5b, "CALLDATALOAD": 0x35, "CALLDATASIZE": 0x36, "CALLDATACOPY": 0x37, "GAS": 0x5a, "CALL": 0xf1, "RETURN": 0xf3, "REVERT": 0xfd,
      "RETURNDATASIZE": 0x3d, "RETURNDATACOPY": 0x3e, "SWAP2": 0x91}
for i in range(1, 17): OP[f"DUP{i}"] = 0x7f + i
SRC = """
PUSH1 0 PUSH1 0
loop: JUMPDEST
DUP2 CALLDATASIZE GT PUSH2 @body JUMPI
PUSH1 0x20 MUL PUSH1 0 RETURN
body: JUMPDEST
DUP2 PUSH1 0x20 ADD CALLDATALOAD
DUP1 DUP4 PUSH1 0x40 ADD PUSH2 0x1000 CALLDATACOPY
PUSH1 0x20 DUP3 PUSH1 0x20 MUL DUP3 PUSH2 0x1000 PUSH1 0 DUP8 CALLDATALOAD GAS CALL
ISZERO PUSH2 @fail JUMPI
PUSH1 0x1f ADD PUSH1 0x1f NOT AND PUSH1 0x40 ADD DUP3 ADD SWAP2 POP PUSH1 1 ADD PUSH2 @loop JUMP
fail: JUMPDEST
POP PUSH1 0 MSTORE RETURNDATASIZE PUSH1 0 PUSH1 0x20 RETURNDATACOPY RETURNDATASIZE PUSH1 0x20 ADD PUSH1 0 REVERT
"""
def assemble(src=SRC):
    toks = src.split(); labels = {}; out = []
    for pass_ in (0, 1):
        out = bytearray(); i = 0
        while i < len(toks):
            t = toks[i]
            if t.endswith(":"): labels[t[:-1]] = len(out); i += 1; continue
            if t.startswith("PUSH"):
                n = int(t[4:]); arg = toks[i + 1]; v = labels.get(arg[1:], 0) if arg.startswith("@") else int(arg, 0)
                out.append(0x5f + n); out += v.to_bytes(n, "big"); i += 2; continue
            out.append(OP[t]); i += 1
    return "0x" + out.hex()
def encode(calls):
    """calls = [(target_address, data_hex)] -> harness calldata"""
    s = ""
    for to, data in calls:
        d = data[2:] if data.startswith("0x") else data; n = len(d) // 2
        s += to[2:].lower().rjust(64, "0") + f"{n:064x}" + d + "0" * ((-len(d)) % 64)
    return "0x" + s
if __name__ == "__main__": print(assemble())
