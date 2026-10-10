import sys, runpy, threading, time
mode = sys.argv[1]
if mode == "switch":
    sys.setswitchinterval(1e-6)
elif mode == "hog":
    def hog():
        x = 0
        while True:
            x += 1
    for _ in range(3):
        threading.Thread(target=hog, daemon=True).start()
sys.argv = ["tests/test_engine.py"]
runpy.run_path("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/review06_concurrency/c2d9fcb/tests/test_engine.py", run_name="__main__")
