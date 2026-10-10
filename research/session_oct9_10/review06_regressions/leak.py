# _oneoff's error path: does the connection's socket stay open after the function returns? (plain HTTP stand-in, same code shape)
import http.client, json, os, socket, threading
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(64); port = srv.getsockname()[1]
def serve():
    while True:
        s, _ = srv.accept(); s.recv(65536); s.close()          # read the request, then hang up: getresponse raises
threading.Thread(target=serve, daemon=True).start()
def oneoff(body):
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=4); c.connect()
        c.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        c.request("POST", "/", body, {"Content-Type": "application/json"}); r = c.getresponse(); data = r.read(); c.close()
        return json.loads(data)
    except Exception as e:
        return {"error": {"message": f"send failed (one-off connection): {e}"}}
nfd = lambda: len(os.listdir("/proc/self/fd"))
base = nfd()
for _ in range(200):
    rep = oneoff(b"{}")
print(rep, "fds before", base, "after 200 failing one-offs", nfd())
