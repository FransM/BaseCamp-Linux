#!/usr/bin/env python3
"""CLI tool to send commands to the LED API plugin."""
import json
import os
import socket
import sys

SOCKET_PATH = os.path.expanduser(
    "~/.config/mountain-time-sync/led_api.sock")

def send(cmd):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCKET_PATH)
    sock.sendall(json.dumps(cmd).encode())
    resp = json.loads(sock.recv(4096).decode())
    sock.close()
    return resp

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cli.py get-status | set-brightness <percent>")
        sys.exit(1)
    if sys.argv[1] == "get-status":
        print(send({"cmd": "get_status"}))
    elif sys.argv[1] == "set-brightness":
        print(send({"cmd": "set_brightness", "percent": int(sys.argv[2])}))
