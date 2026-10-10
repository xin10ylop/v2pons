import sys
def scan(code):
    b = bytes.fromhex(code[2:]); i = 0; p4 = []; p32 = []; p20 = []
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f; v = b[i+1:i+1+n]
            if n == 4: p4.append(v.hex())
            if n == 32: p32.append(v.hex())
            if n == 20: p20.append(v.hex())
            i += n + 1
        else: i += 1
    return p4, p32, p20
for f in sys.argv[1:]:
    c = open(f).read().strip()
    p4, p32, p20 = scan(c)
    seen = []
    [seen.append(x) for x in p4 if x not in seen]
    print(f, "PUSH4:", " ".join(seen))
    print("  PUSH32:", [x for x in p32 if not x.startswith("ffffffff") and x.strip('0')])
    print("  PUSH20:", p20)
    print("  DELEGATECALL" if "f4" in c else "", "CREATE2:", "f5" in c, "SELFDESTRUCT:", "ff" in c)
