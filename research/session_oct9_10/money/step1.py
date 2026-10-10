from tr import *
# the three 7-ETH recipients from today's pulls, and the extra source of 0xaee54a9f
cases = [("0xaee54a9fb9cede0fd7360283894c7fb6d35d8bd4", 84122311 + 298), ("0xcb4cc2f47d729315d900b2b1c36e43df862ab9c8", 84123041 + 82), ("0x6ddf48a50d018499833efb31af96cb54fd1fbf31", 84123471 + 76)]
for hop, b in cases:
    print("== hop", hop)
    for n, t in touching([hop], b - 400, b + 200): print("  ", show(n, t, b))
for r in ("0xdb1b7d290eceaa5efe8e735f913e9e8bc3c38a48", "0xd69c3707bfd79d846c8362d036b8de6ea5022529", "0x99b5ef5bc5fea5485a230a405aff7da38122d345"):
    print("== 7 ETH recipient", r)
    for n, t in touching([r], 84121500, 84126800): print("  ", show(n, t))
save()
