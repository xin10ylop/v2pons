import sys, runpy, threading, time
_orig = threading.Thread.run
def run(self):
    if getattr(self, "_target", None) is not None and self._target.__name__ == "deliver_sell":
        time.sleep(float(sys.argv[2]))          # the OS schedules the new thread a little later
    return _orig(self)
threading.Thread.run = run
runpy.run_path(sys.argv[1], run_name="__main__")
