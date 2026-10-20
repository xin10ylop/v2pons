import sys, trace, os, runpy, collections
hits = collections.Counter()
SRC = "/home/user/v2pons/src/flip_engine.py"
def tracer(frame, event, arg):
    if frame.f_code.co_filename == SRC:
        if event == "line": hits[frame.f_lineno] += 1
        return tracer
    return tracer
import threading
threading.settrace(tracer); sys.settrace(tracer)
os.chdir("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/verify_engine")
sys.argv = ["test_engine.py"]
try:
    runpy.run_path("/home/user/v2pons/tests/test_engine.py", run_name="__main__")
finally:
    sys.settrace(None)
    import json; json.dump(sorted(hits), open("hits.json", "w"))
