import json, base64, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"); sys.path.insert(0, "/home/user/v2pons/src")
import chain, flip_engine as E
from eth_utils import keccak
for line in open("frames.txt"):
    for m in json.loads(line).get("messages", []):
        inner = m["message"]["message"]; raw = base64.b64decode(inner.get("l2Msg", ""))
        if raw and raw[0] == 4:
            seq = m["sequenceNumber"]; tx = raw[1:]; h = keccak(tx).hex()
            print("seq", seq, "kind4 len", len(raw), "engine decode_batch ->", E.decode_batch(inner["l2Msg"]), "tx hash 0x" + h, "parse_tx ok:", E.parse_tx(tx) is not None)
            b = chain.rpc("eth_getBlockByNumber", [hex(seq), False]); print("block", int(b["number"],16), "txs", b["transactions"])
            # neighbours
            for s in (seq - 1, seq + 1):
                bb = chain.rpc("eth_getBlockByNumber", [hex(s), False]); print(" block", s, "ntx", len(bb["transactions"]))
