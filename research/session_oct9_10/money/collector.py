import json
from tr import *
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
crowd = set(json.load(open("deployers.json"))["crowd"])
A32 = {"0x754425071f61539f3ca0106634d9f88850c8a151", "0xdc2e86611b27dc4209dc4055ae4f7cf5b9ee5e80", "0x295877ce91a25528ae17263cb3d30eb11bbfae3e", "0xe6af9036d2e9317edc710bb769c9808168f8b4ad",
       "0x8700722d7a", "0x5861708803b8b73b2df8d985bed333b88c92dcc0", "0x20d811c806351d2edc6cb297f6e75e954bf443a5"}
found = []
for s in range(83481207, 83481207 + 6000, 300):
    for n, t in touching([C], s, s + 299):
        found.append((n, t)); print(show(n, t, 83481207), "| crowd" if (t[2] in crowd or t[1] in crowd) else "", flush=True)
    if sum(1 for n, t in found if t[1] == C) >= 6: break
save()
