import sys
p = sys.argv[1]; s = open(p).read()
a = "the bot's incrementing fee tiers 10001-10300 (9.333/33.333/4.0 ETH, 97 pools)"
b = ("the bot's incrementing fee tiers 10001-10300 of HANDOFF section 1 (97 pools, fees 10047-10224, tick spacing 200-204, values 9.333 x 60, "
     "40 x 30, 33.333 x 5, 4.0 x 2; none of them shows the bot's router: 34 are pulled through the POSM, 63 not within 3,000 blocks, so this "
     "label rests on the handoff's description of those families only)")
assert a in s; s = s.replace(a, b); open(p, "w").write(s); print("ok")
