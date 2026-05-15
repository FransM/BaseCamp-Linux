"""PyInstaller runtime hook — runs BEFORE the entry script.

If a source-overlay directory with a VERSION file exists under
~/.local/share/basecamp-linux/source-overlay/, prepend it to sys.path so
that user modules (gui, shared, devices, plugins, ...) resolve to the
overlay's .py files instead of the bundled .pyc copies in _internal/.

Native deps (customtkinter, PIL, hid, ...) stay bundled — the overlay
only ever contains pure-Python code, so this can't break the runtime.
A broken/empty overlay is silently ignored.
"""
import os
import sys

try:
    _overlay = os.path.join(os.path.expanduser("~"),
                            ".local", "share", "basecamp-linux",
                            "source-overlay")
    _version = os.path.join(_overlay, "VERSION")
    if os.path.isdir(_overlay) and os.path.isfile(_version):
        with open(_version, "r", encoding="utf-8") as _f:
            _ver = _f.read().strip()
        # Sanity: a 'gui.py' must be present, otherwise the overlay is
        # incomplete / mid-extraction and we'd crash on import.
        if _ver and os.path.isfile(os.path.join(_overlay, "gui.py")):
            sys.path.insert(0, _overlay)
            os.environ["BASECAMP_OVERLAY_VERSION"] = _ver
except Exception:
    pass
