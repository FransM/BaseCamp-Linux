#!/usr/bin/env python3
"""Tray icon helper — runs as real user, communicates with main GUI via signals.

Resilient against the X11 systray manager going away (desktop panel restart,
notification area recreated, idle reaping). pystray's Xorg backend raises
``AssertionError`` from ``_assert_docked`` / ``_on_destroy_notify`` when the
systray host window is destroyed; left unhandled that kills the tray icon for
good (GitHub issue #21). We supervise ``icon.run()`` and simply re-dock.

The logic lives in main() so a thin frozen entry (tray_entry.py) can import it,
which lets the source overlay replace this file for live updates (issue #20
follow-up). Run directly (`python tray_helper.py <pid> [lang.json]`) still works.
"""
import sys, os, signal, json, time
import pystray
from PIL import Image


def _res_dir():
    """Directory holding bundled resources (icons). Resolves to the PyInstaller
    bundle when frozen — NOT to a source overlay, which has no resources/."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main():
    main_pid = int(sys.argv[1])

    # Optional 3rd argument: path to lang JSON file
    open_label, quit_label = "Open", "Quit"
    if len(sys.argv) >= 3:
        lang_file = sys.argv[2]
        lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang")
        if not os.path.abspath(lang_file).startswith(lang_dir):
            lang_file = None
        try:
            with open(lang_file, encoding="utf-8") as f:
                lang = json.load(f)
            open_label = lang.get("tray_open", open_label)
            quit_label = lang.get("tray_quit", quit_label)
        except Exception:
            pass

    state = {"run": True}  # cleared on explicit Quit so we don't re-dock after

    def on_open(icon, item):
        os.kill(main_pid, signal.SIGUSR1)

    def on_quit(icon, item):
        state["run"] = False
        try:
            os.kill(main_pid, signal.SIGUSR2)
        except OSError:
            pass
        icon.stop()

    def main_alive():
        """True while the GUI process we belong to is still running."""
        try:
            os.kill(main_pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def build_icon():
        img = Image.open(os.path.join(_res_dir(), "resources", "app_icon_32.png"))
        menu = pystray.Menu(
            pystray.MenuItem(open_label, on_open, default=True),
            pystray.MenuItem(quit_label, on_quit),
        )
        return pystray.Icon("MountainEvMax", img, "Mountain Everest Max", menu)

    # Supervise the tray. If the systray manager disappears, pystray raises out
    # of run() (or run() returns); rebuild and re-dock as long as the GUI is
    # alive and the user hasn't quit. Back off when no systray host is present so
    # we don't busy-loop, but reset once an icon has stayed docked for a while.
    backoff = 1.0
    while state["run"] and main_alive():
        started = time.monotonic()
        try:
            build_icon().run()
        except Exception as e:
            print(f"[Tray] {type(e).__name__}: {e} — re-docking", file=sys.stderr)
        if not state["run"] or not main_alive():
            break
        if time.monotonic() - started > 5.0:
            backoff = 1.0
        time.sleep(backoff)
        backoff = min(backoff * 2, 30.0)


if __name__ == "__main__":
    main()
