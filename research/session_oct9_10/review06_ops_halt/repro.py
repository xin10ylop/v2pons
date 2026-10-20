import sys, os, importlib.util, json, time
D = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r", os.path.join(D, "results_c2d.py")); r = importlib.util.module_from_spec(spec)
sys.argv = ["results.py", "24"]; spec.loader.exec_module(r)
halt = os.path.join(D, "HALTED"); log = os.path.join(D, "engine.jsonl")
open(halt, "w").close()   # empty file (touch / truncated write)
now = time.time()
with open(log, "w") as f:
    f.write(json.dumps({"t": now-60, "ev": "start", "dry_run": False, "release": "0.6", "halted": "halted"}) + "\n")
    f.write(json.dumps({"t": now-30, "ev": "flow", "halted": "halted"}) + "\n")
r.HALT = halt; r.LOG = log; r.ENV = "/nonexistent"; r.balance = lambda *a: None
r.main()
# engine side
os.environ["HALT_FILE"] = halt
