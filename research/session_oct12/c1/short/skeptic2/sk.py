"""Skeptic 2 (execution lens) helpers for the C-1 short-exit study. Reuses ../../common.py and the paced ../../rpc.py unchanged
(one POST >= 0.5 s apart, read methods only, back-off on 429); its log goes to this directory. Read-only; no key, no transaction."""
import os, sys, json
_ME = os.path.dirname(os.path.abspath(__file__)); _SHORT = os.path.dirname(_ME); _C1 = os.path.dirname(_SHORT)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_C1))), "src")
sys.path.insert(0, _C1); sys.dont_write_bytecode = True
from common import *          # noqa: F401,F403
import rpc
rpc.LOG = os.path.join(_ME, "rpc_log.jsonl")
K = lambda n: os.path.join(_ME, n)          # my outputs
SH = lambda n: os.path.join(_SHORT, n)      # the analyst's (data only)
sys.path.insert(0, _SRC)
import v4math                               # the engine's own swap math (src/v4math.py)
