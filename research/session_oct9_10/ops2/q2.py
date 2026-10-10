import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
print(len(A), len(B), len(DISP), len(SWEEP), len(FAM))
for r in touching([C], 83396250, 83403249, cached_only=True):
    print(fmt(r), lab(r["from"]), "->", lab(r["to"]))
