import sys
p = sys.argv[1]; s = open(p).read()
rep = [("| 0xe51960f1b45f1c9fb6d166e6a884f866fc70433b | V3 PoolCreated | 19 | 0 |", "| 0xe51960f1b45f1c9fb6d166e6a884f866fc70433b | V3 PoolCreated | 19 | 2 |"),
       ("| 0x221a6239e40709792b0d4bdc140fa36158cd41c7 | V3 PoolCreated | 10 | 0 (GOO) |", "| 0x221a6239e40709792b0d4bdc140fa36158cd41c7 | V3 PoolCreated | 10 | 1 (mostly GOO) |"),
       ("| 0x43b2bf9f33036a02fc7a00935571c2a6b0108e66 | V2 PairCreated | 10 | 0 (USDG) |", "| 0x43b2bf9f33036a02fc7a00935571c2a6b0108e66 | V2 PairCreated | 10 | 1 (mostly USDG) |"),
       ("26 code hashes, 5 deployers; calldata 740-836 bytes, fee 10000, ts 200, hooks set)", "26 code hashes, 5 deployers; calldata 644-964 bytes in steps of 32, fee 10000, ts 200, hooks 0x0)"),
       ("1,751 POSTs, 192 answered 429 (retried with backoff, every one recovered). Nothing failed.",
        "About 1,800 POSTs (1,797 counted by the stages), 192 answered HTTP 429 (retried with backoff; every one recovered). Nothing failed:\n0 null transactions, 0 unanswered batch items, no stage restarted."),
       ("1,323 with its router)", "1,323 with its router; values 3.0 x 889, 5.0 x 434, 0 x 15, 1e-6 x 1)"),
       ("is in 1,048 of the 1,843 v2.433 pools (front, 0.0058 ETH at launch + 1) and in operator A's;",
        "is among the first 8 swaps of 1,048 of the 1,843 v2.433 pools (front, 0.0058 ETH at launch + 1) and of 35 of operator A's 77;"),
       ("| 183 + 65 | 557 queries,", "| 183 + 65 | 557 groups,")]
for a, b in rep:
    assert a in s, a[:60]
    s = s.replace(a, b)
open(p, "w").write(s)
print("ok")
