"""Tiny PyInstaller entry shim for the Makalu 67 / Max mouse controller.

The real logic lives in the importable module devices/makalu67/controller.py,
so the source overlay can replace it for live updates — exactly like appentry.py
does for the GUI. _overlay_bootstrap.py (a runtime hook) inserts the user's
source-overlay dir into sys.path before this runs.

Build the makalu-controller binary from this file; never put logic here.
"""
from devices.makalu67 import controller


if __name__ == "__main__":
    controller.main()
