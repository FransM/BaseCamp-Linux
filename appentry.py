"""Tiny PyInstaller entry script.

The actual app lives in gui.py — this shim exists so that the bundled
entry stays stable across patches. When _overlay_bootstrap.py runs (as a
runtime hook) it inserts the user's source-overlay dir into sys.path; the
plain `import gui` below then resolves to the overlay's gui.py if present.

Build everything from this file via PyInstaller; never edit it.
"""
import gui


if __name__ == "__main__":
    gui.run()
