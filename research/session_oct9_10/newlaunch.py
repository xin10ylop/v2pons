import json, time, collections, rlp
from eth_utils import keccak
from chain import *
head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83380000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
sel = [(l, t) for l, t in zip(inits, txs) if t and t["input"][:10] == "0x2fcb9108"]
opcode = rpc("eth_getCode", ["0x" + OP, "latest"])
print(f"launches with the operator's call 0x2fcb9108 since 14:10: {len(sel)}; the old launcher's code {len(opcode)//2-1} bytes, keccak {keccak(bytes.fromhex(opcode[2:])).hex()[:12]}")
codes = batch([("eth_getCode", [t["to"], "latest"]) for l, t in sel])
bts = batch([("eth_getBlockByNumber", [l["blockNumber"], False]) for l, t in sel])
rows = []
for (l, t), c, b in zip(sel, codes, bts):
    frm = t["from"]; to = t["to"].lower()
    created = "0x" + keccak(rlp.encode([bytes.fromhex(frm[2:]), 0]))[12:].hex()          # the deployer's nonce-0 CREATE address
    d = l["data"]; pid = l["topics"][1]; bn = int(l["blockNumber"], 16)
    rows.append((pid, bn, l))
    print(f"  {time.strftime('%H:%M:%S', time.gmtime(int(b['timestamp'], 16)))} fee {W(d,0)/1e4:.4g}% launcher {to[:10]} {'= the old one' if to[2:] == OP else ('deployed by this deployer at nonce 0' if created == to else 'other')}, code {len(c)//2-1} B {'same as old' if c == opcode else 'keccak ' + keccak(bytes.fromhex(c[2:])).hex()[:12]}, deployer nonce {int(t['nonce'],16)}")
json.dump([(p, bn) for p, bn, _ in rows], open("newlaunch.json", "w"))
