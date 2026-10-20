#!/usr/bin/env python3
"""new_wallet.py: create the flip engine's own wallet on the box and write it into /etc/flip/engine.env (WALLET= and PRIVATE_KEY=,
mode 600). The key is never printed: only the address, which is what you send the ETH to. Refuses to replace a key already set.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/new_wallet.py

To back the key up, read it on your own screen with `sudo grep PRIVATE_KEY /etc/flip/engine.env` and keep it in a password manager;
never paste it into a chat, a ticket or a repository."""
import os, re, sys
from eth_account import Account

p = sys.argv[1] if len(sys.argv) > 1 else "/etc/flip/engine.env"
s = open(p).read()
if re.search(r"^PRIVATE_KEY=0x[0-9a-fA-F]{64}\s*$", s, re.M):
    sys.exit(f"a key is already set in {p}: not replacing it")
if not re.search(r"^WALLET=", s, re.M) or not re.search(r"^PRIVATE_KEY=", s, re.M):
    sys.exit(f"{p} has no WALLET= or PRIVATE_KEY= line: run deploy/flip_setup.sh first")
a = Account.create()
key = "0x" + a.key.hex().removeprefix("0x")
s = re.sub(r"^WALLET=.*$", "WALLET=" + a.address.lower(), s, flags=re.M)
s = re.sub(r"^PRIVATE_KEY=.*$", "PRIVATE_KEY=" + key, s, flags=re.M)
tmp = p + ".tmp"; open(tmp, "w").write(s); os.chmod(tmp, 0o600); os.replace(tmp, p)
chk = open(p).read()
w = re.search(r"^WALLET=(0x[0-9a-f]{40})$", chk, re.M).group(1); k = re.search(r"^PRIVATE_KEY=(0x[0-9a-f]{64})$", chk, re.M).group(1)
assert Account.from_key(k).address.lower() == w, "the written key does not match the written address"
print(f"new flip wallet: {Account.from_key(k).address}")
print("send about $50 of ETH to it on Robinhood Chain (chain id 4663), then: sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status")
