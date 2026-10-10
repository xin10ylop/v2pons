import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_27")
from rpcc import call, call_many
hook = "0xd75141462ab9630d3969469805016e7e27b54080"
code = call("eth_getCode", [hook, "latest"])
b = bytes.fromhex(code[2:])
# minimal disassembler
OP = {0x00:"STOP",0x01:"ADD",0x02:"MUL",0x03:"SUB",0x04:"DIV",0x05:"SDIV",0x06:"MOD",0x0a:"EXP",0x10:"LT",0x11:"GT",0x12:"SLT",0x13:"SGT",0x14:"EQ",0x15:"ISZERO",0x16:"AND",0x17:"OR",0x18:"XOR",0x19:"NOT",0x1a:"BYTE",0x1b:"SHL",0x1c:"SHR",0x1d:"SAR",0x20:"SHA3",0x30:"ADDRESS",0x31:"BALANCE",0x32:"ORIGIN",0x33:"CALLER",0x34:"CALLVALUE",0x35:"CALLDATALOAD",0x36:"CALLDATASIZE",0x37:"CALLDATACOPY",0x38:"CODESIZE",0x39:"CODECOPY",0x3a:"GASPRICE",0x3b:"EXTCODESIZE",0x3d:"RETURNDATASIZE",0x3e:"RETURNDATACOPY",0x3f:"EXTCODEHASH",0x40:"BLOCKHASH",0x41:"COINBASE",0x42:"TIMESTAMP",0x43:"NUMBER",0x44:"PREVRANDAO",0x45:"GASLIMIT",0x46:"CHAINID",0x47:"SELFBALANCE",0x48:"BASEFEE",0x50:"POP",0x51:"MLOAD",0x52:"MSTORE",0x53:"MSTORE8",0x54:"SLOAD",0x55:"SSTORE",0x56:"JUMP",0x57:"JUMPI",0x58:"PC",0x59:"MSIZE",0x5a:"GAS",0x5b:"JUMPDEST",0x5c:"TLOAD",0x5d:"TSTORE",0x5e:"MCOPY",0x5f:"PUSH0",0xf0:"CREATE",0xf1:"CALL",0xf2:"CALLCODE",0xf3:"RETURN",0xf4:"DELEGATECALL",0xf5:"CREATE2",0xfa:"STATICCALL",0xfd:"REVERT",0xfe:"INVALID",0xff:"SELFDESTRUCT"}
i = 0
while i < len(b):
    o = b[i]
    if 0x60 <= o <= 0x7f:
        n = o - 0x5f; print("%04x PUSH%d 0x%s" % (i, n, b[i+1:i+1+n].hex())); i += 1 + n; continue
    if 0x80 <= o <= 0x8f: print("%04x DUP%d" % (i, o - 0x7f))
    elif 0x90 <= o <= 0x9f: print("%04x SWAP%d" % (i, o - 0x8f))
    elif 0xa0 <= o <= 0xa4: print("%04x LOG%d" % (i, o - 0xa0))
    else: print("%04x %s" % (i, OP.get(o, "0x%02x" % o)))
    i += 1
