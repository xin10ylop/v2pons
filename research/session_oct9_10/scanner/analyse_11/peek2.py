import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); TF = load_to_families(); LF = load_loose_families()
for k, v in TF.items():
    if k.startswith("0x387a453d") or k.startswith("0x0000ffffbe8e") or k.startswith("0xa1c9c202") or k.startswith("0xdf4ca4e1"):
        print(k, json.dumps(v)[:600])
for k, v in LF.items():
    if k.startswith("54e231e6") or k.startswith("7fde822e|772") or k.startswith("ac9650d8|1476"):
        print(k, json.dumps(v)[:600])
# all pools launched by the same deployers / to the same launch contracts
deps = {"0x970dcc45e066464dcc2cd54c0dbd08859c5d0951", "0xcfa921b4f8a9a549c361ec93cbb045ba9f6f24c0", "0xc0b3535e207830706656016b62806d8fe9e6ae6e", "0x26e8134ecc3af5cce32f34b03e7bd2f318b25158", "0x6cd65489492324353cd04a1a9a37ea616bbbfb26", "0x99339fd42e91cd08e527b71fe127d360eadc9c11", "0x692f74bc"}
c = collections.Counter()
for pid, r in P.items():
    if r["launch_from"] in deps or r["launch_from"].startswith("0x692f74bc") or r["launch_to"] in ("0x387a453d75a1b8fa825a9b9d4ad87323c0f48755", "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0"):
        c[(r["launch_from"][:10], r["launch_to"][:10] if r["launch_to"] else None, r["selector"], r["calldata_len"], r["fee"], r["tick_spacing"], r["hooks"][:10], r["family"] [:20])] += 1
for k, v in sorted(c.items()): print(v, k)
