"""full tx hashes (from the block cache) for the money links cited in the conclusion"""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
L = [(83386507, "0x1821144f", "0x3194e326"), (83396408, "0x1821144f", ""), (83396649, "0x1821144f", "0xded28cc0"), (83396670, "0xded28cc0", "0x58fc6f17"),
     (83396678, "0x58fc6f17", "0x3fc5b8b8"), (83396685, "0x58fc6f17", "0x4c45af68"), (83397167, "0x4c45af68", "0x3fc5b8b8"),
     (83385919, "0x9614ea90", "0x4001b198"), (83385934, "0x4001b198", "0xa59d8f2c"), (83385942, "0xa59d8f2c", "0x1821144f"),
     (83402292, "0x3fc5b8b8", "0xfcfdd782"), (83481215, "0x54c46371", "0x3fc5b8b8"), (83492168, "0x3fc5b8b8", "0x1d18f103"), (83492178, "0x1d18f103", "0xe50dd00a"),
     (83492185, "0xe50dd00a", "0x7a95cedb"), (83492192, "0xe50dd00a", "0x4c45af68"), (83498324, "0x7a95cedb", "0xdb1e05f3"), (83498345, "0xdb1e05f3", "0xf73fa652"),
     (83419172, "0x9614ea90", "0x3fc5b8b8"), (83419183, "0x6cdcd541", "0x3fc5b8b8"), (83419163, "0x58fc6f17", "0x3fc5b8b8"),
     (83290636, "0xc0fc363a", "0xb63b68dc"), (83303420, "0xb63b68dc", "0x3ee51814"), (83647788, "0xb63b68dc", "0xc139beb5"), (83647811, "0xc139beb5", "0x501f4f53"),
     (83647818, "0x501f4f53", "0x4348ffca"), (83647803, "0x58617088", "0xc139beb5"), (83362505, "0x3ee51814", "0xdef59ef1"), (83364161, "0xdef59ef1", "0x3ee51814"),
     (83304006, "0x3ee51814", "0x6564816d"),
     (83340951, "0x583fec35", "0xd4b94999"), (83341074, "0x1f2e5395", "0x5477a0da"), (83341090, "0x5477a0da", "0x6e7dde8e"), (83341099, "0x5477a0da", "0x5b18301c"),
     (83341137, "0x5b18301c", "0x94e12c34"), (83342245, "0x94e12c34", "0x92b66c43"), (83342239, "0x1b676fa7", "0x92b66c43"), (83352773, "0x1fd5451b", "0x58daec31"),
     (83288800, "0x8a10f14e", "0x0f77ceec")]
out = []
for bn, f, t in L:
    c = bc.chunk(bn // bc.CH) if have(bn // bc.CH) else None
    if not c or bn not in c: print("not cached", bn); continue
    for x in c[bn][1]:
        if x[1].startswith(f) and (not t or x[2].startswith(t)):
            out.append({"block": bn, "tx": x[0], "from": x[1], "to": x[2], "eth": int(x[3]) / 1e18, "nonce": x[4], "sel": x[5]}); print(bn, x[0], x[1], x[2], int(x[3]) / 1e18, "n", x[4], x[5])
json.dump(out, open("links.json", "w"), indent=1)
