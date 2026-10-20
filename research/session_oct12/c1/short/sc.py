"""shared helpers for the short-exit study (session_oct12/c1/short). Reuses ../common.py and the paced ../rpc.py unchanged (one POST
>= 0.5 s apart, read methods only, back-off on 429); only its log is redirected here. Read-only; no key, no transaction."""
import os, sys
_SHORT = os.path.dirname(os.path.abspath(__file__)); _C1 = os.path.dirname(_SHORT)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_C1))), "src")
sys.path.insert(0, _C1); sys.dont_write_bytecode = True
from common import *                      # noqa: F401,F403  (J() points at ../ for the C1R caches)
import rpc
rpc.LOG = os.path.join(_SHORT, "rpc_log.jsonl")
S = lambda n: os.path.join(_SHORT, n)     # outputs of this study
sys.path.insert(0, _SRC)
import v4math                             # the engine's own swap math (src/v4math.py)
