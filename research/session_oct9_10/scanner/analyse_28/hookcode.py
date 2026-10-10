import json, re, sys
R = json.load(open("hookfee_rcpts.json"))
for a, c in R["_code"].items():
    b = bytes.fromhex(c[2:]); sels = []
    i = 0
    while i < len(b):
        op = b[i]
        if op == 0x63: sels.append(b[i+1:i+5].hex())
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    print(a, len(b), sorted(set(sels)))
