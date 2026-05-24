"""Tiny PyInstaller entry shim for the tray helper.

The real logic lives in the importable module tray_helper.py, so the source
overlay can replace it for live updates — like appentry.py does for the GUI.
_overlay_bootstrap.py (a runtime hook) inserts the user's source-overlay dir
into sys.path before this runs.

Build the basecamp-tray binary from this file; never put logic here.
"""
import tray_helper


if __name__ == "__main__":
    tray_helper.main()
