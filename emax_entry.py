"""Tiny PyInstaller entry shim for the Everest Max controller / button daemon.

The real logic lives in the importable module emax_controller.py, so the source
overlay can replace it for live updates — exactly like appentry.py does for the
GUI. _overlay_bootstrap.py (a runtime hook) inserts the user's source-overlay
dir into sys.path before this runs, so the import below resolves to the overlay
copy when present.

Build the basecamp-controller binary from this file; never put logic here.
"""
import emax_controller


if __name__ == "__main__":
    emax_controller.main()
