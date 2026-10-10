# The c2d9fcb Sender against a local server whose replies take RTT_MS: sends fired at random moments while the keepalive runs.
# How many sends fall back to a one-off connection?
import os, sys, time, json, random, socket, threading, http.client, http.server, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("LOG_PATH", tempfile.mktemp())
import fe_c2d9fcb as E
RTT = float(sys.argv[1]) / 1000; DUR = float(sys.argv[2])
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"])); time.sleep(RTT)
        b = b'{"jsonrpc":"2.0","id":1,"result":"0x1"}'; self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
class C(http.client.HTTPConnection):
    def __init__(self, host, port, timeout=4, context=None): super().__init__(host, port, timeout=timeout)
E.http.client.HTTPSConnection = C
s = E.Sender(f"http://127.0.0.1:{srv.server_address[1]}/")
n_oneoff = [0]; orig = s._oneoff
def counting(body): n_oneoff[0] += 1; return orig(body)
s._oneoff = counting
n = 0; t_end = time.monotonic() + DUR
while time.monotonic() < t_end:
    time.sleep(random.uniform(0.0, 0.4)); s.last[0] = 0.0 if random.random() < 0.0 else s.last[0]
    s.post(0, b'{"jsonrpc":"2.0","id":1,"method":"eth_sendRawTransaction","params":[]}'); n += 1
    s.last[0] = time.monotonic() - 5.0 - random.uniform(0, 1.0)     # force the slot idle so the keepalive pings it often (worst case)
print(f"RTT {RTT*1000:.0f} ms: {n} sends, {n_oneoff[0]} fell back to a one-off connection")
