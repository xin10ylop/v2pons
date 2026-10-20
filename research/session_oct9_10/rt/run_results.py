import sys, json, time, subprocess, importlib.util, os
logp = sys.argv[1]
spec = importlib.util.spec_from_file_location("results", "/home/user/v2pons/deploy/results.py")
sys.argv = ["results.py", "24"]
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
R.LOG = logp; R.ENV = "/nonexistent"; R.HALT = logp + ".HALTED"
class P: returncode = 1
R.subprocess.run = lambda *a, **k: P()
R.main()
