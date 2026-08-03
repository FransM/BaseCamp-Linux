import json
import os
import socket
import threading

SOCKET_PATH = os.path.expanduser(
    "~/.config/mountain-time-sync/led_api.sock")


class Plugin:
    def __init__(self, ctx):
        self.ctx = ctx
        self._stop = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        # Unlink socket to unblock accept()
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKET_PATH)
            sock.close()
        except Exception:
            pass
        try:
            os.unlink(SOCKET_PATH)
        except Exception:
            pass

    def _serve(self):
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(SOCKET_PATH)
        srv.listen(1)
        srv.settimeout(1.0)
        print(f"[LED API] Listening on {SOCKET_PATH}", flush=True)

        while not self._stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            try:
                data = conn.recv(4096).decode()
                cmd = json.loads(data)
                result = self._handle(cmd)
                conn.sendall(json.dumps(result).encode())
            except Exception as e:
                conn.sendall(json.dumps({"ok": False, "error": str(e)}).encode())
            finally:
                conn.close()

        srv.close()
        try:
            os.unlink(SOCKET_PATH)
        except Exception:
            pass

    def _handle(self, cmd):
        action = cmd.get("cmd")
        if action == "get_status":
            kb = self.ctx.get_keyboard_panel()
            return {"ok": True, "keyboard_connected": kb is not None}
        if action == "set_brightness":
            # Example: adjust brightness via the keyboard panel
            percent = cmd.get("percent", 100)
            print(f"[LED API] Set brightness to {percent}%", flush=True)
            return {"ok": True}
        return {"ok": False, "error": f"Unknown command: {action}"}
