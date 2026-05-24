"""Tiny PyInstaller entry shim for the Everest 60 controller.

The real logic lives in the importable module devices/everest60/controller.py,
so the source overlay can replace it for live updates — exactly like appentry.py
does for the GUI. _overlay_bootstrap.py (a runtime hook) inserts the user's
source-overlay dir into sys.path before this runs, so the import below resolves
to the overlay copy when present.

Build the everest60-controller binary from this file; never put logic here.
"""
from devices.everest60 import controller


if __name__ == "__main__":
    controller.main()
