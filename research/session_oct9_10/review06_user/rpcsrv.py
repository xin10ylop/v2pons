import http.server, json, sys, time
mode = sys.argv[2] if len(sys.argv) > 2 else "ok"
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); req = json.loads(self.rfile.read(n))
        if mode == "hang": time.sleep(60)
        if mode == "err": body = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "rate limited"}}
        elif mode == "html": self.send_response(502); self.end_headers(); self.wfile.write(b"<html>bad gateway</html>"); return
        else:
            bal = {"0x1111111111111111111111111111111111111111": 0.00291, "0x2222222222222222222222222222222222222222": 0.0031}.get(req["params"][0].lower(), 0)
            body = {"jsonrpc": "2.0", "id": 1, "result": hex(int(bal * 1e18))}
        b = json.dumps(body).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
