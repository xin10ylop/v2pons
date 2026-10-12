#!/usr/bin/env python3
"""bnb_wallet.py: create the BNB line's own wallet on the box (src/bnb_live.py; not the flip engine's wallet, whose key stays in
/etc/flip/engine.env, which this script never opens). A new key goes to /etc/flip/bnb.key, created mode 600 (os.open with O_EXCL: an
existing file is never replaced). The key is never printed: only the address, which is what you send the BNB to, and the BNB_WALLET= line
for /etc/flip/bnb.env.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py

To back the key up, read it on your own screen with `sudo cat /etc/flip/bnb.key` and keep it in a password manager; never paste it
into a chat, a ticket or a repository."""
import os, re, sys
from eth_account import Account

p = sys.argv[1] if len(sys.argv) > 1 else "/etc/flip/bnb.key"
if os.path.basename(p) == "engine.env":
    sys.exit("this script writes the BNB key file only, never the flip engine's env file")
if os.path.lexists(p):
    sys.exit(f"{p} exists: not replacing it (move it away yourself if it really is unused, after backing it up)")
a = Account.create()
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    os.fchmod(fd, 0o600)
    os.write(fd, ("0x" + bytes(a.key).hex() + "\n").encode())
    os.fsync(fd)
finally:
    os.close(fd)
st = os.stat(p)
k = open(p).read().strip()
assert re.fullmatch(r"0x[0-9a-f]{64}", k) and st.st_mode & 0o777 == 0o600, "the key file was not written as expected"
assert Account.from_key(k).address == a.address, "the written key does not match the address"
del k
print(f"new BNB wallet: {a.address}")
print(f"add this line to /etc/flip/bnb.env: BNB_WALLET={a.address.lower()}")
print("send about $20 of BNB to it on BNB Smart Chain (BEP-20, chain id 56); RUNBOOK 4k has the rest")
