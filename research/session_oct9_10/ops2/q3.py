import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
for a, lo, hi in [("0x1d18f10325a5b4fa584dbad259473107a29a79ac", 83481000, 83518499), ("0x58fc6f17ea0d2e472867fed709cedb6b131a40dc", 83396250, 83403249)]:
    print("==", a)
    for r in touching([a], lo, hi, cached_only=True):
        print("  ", fmt(r), lab(r["from"]), "->", lab(r["to"]))
