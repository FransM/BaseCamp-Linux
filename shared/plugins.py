"""PluginManager -- discovers and loads plugins from ~/.config/mountain-time-sync/plugins/."""
import os
import sys
import json
import importlib.util

from shared.config import CONFIG_DIR, PLUGINS_DISABLED_FILE

# Set BASECAMP_PAGE_DEBUG=1 in the environment to trace page-scoped
# start/stop decisions (also toggles matching trace lines in
# devices/displaypad/panel.py and page-bound widget plugins). Off by default.
_DEBUG = os.environ.get("BASECAMP_PAGE_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")


def _dbg(msg):
    if _DEBUG:
        print(msg, flush=True)

PLUGINS_DIR = os.path.join(CONFIG_DIR, "plugins")

# A manifest names its dependencies the way pip does, which is not always the
# way import does: "Pillow" imports as PIL, "opencv-python" as cv2. Feeding the
# manifest string straight to __import__ therefore reported Pillow as missing
# everywhere, including in the AppImage that ships it, and the plugin screen
# put a warning dot on plugins that were working fine (#76).
_REQUIREMENT_MODULES = {
    "pillow": "PIL",
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "opencv-contrib-python": "cv2",
    "pyusb": "usb",
    "hidapi": "hid",
    "pyyaml": "yaml",
    "python-dateutil": "dateutil",
    "beautifulsoup4": "bs4",
    "pyserial": "serial",
    "pillow-simd": "PIL",
}


def requirement_module(name):
    """The module name to import for a requirement as spelled in a manifest.

    Strips any version marker ("Pillow>=10") and maps the handful of packages
    whose import name differs from their pip name; everything else keeps its
    own name with dashes turned into underscores, which is the pip convention.
    """
    base = str(name or "").strip()
    for sep in ("<", ">", "=", "!", "~", "[", ";", " "):
        base = base.split(sep)[0]
    base = base.strip()
    if not base:
        return ""
    return _REQUIREMENT_MODULES.get(base.lower(), base.replace("-", "_"))


def has_requirement(name):
    """Is a manifest requirement importable in the interpreter we run in?"""
    mod = requirement_module(name)
    if not mod:
        return True
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        # find_spec raises for a parent package that is itself missing.
        return False


class PluginManager:
    """Scan, load, and manage lifecycle of user plugins."""

    def __init__(self):
        self._manifests = {}     # id -> manifest dict
        self._instances = {}     # id -> Plugin instance
        self._action_types = {}  # type_id -> {"label", "handler"}
        self._disabled = set()   # set of disabled plugin IDs
        self._errors = {}        # id -> error string
        self._running = {}       # id -> bool, service plugins currently start()-ed
        self._loading_pid = None  # set while instantiating a plugin, so
                                   # register_action_type() can tag ownership
        self._load_disabled()

    def _load_disabled(self):
        """Load set of disabled plugin IDs from disk."""
        try:
            with open(PLUGINS_DISABLED_FILE) as f:
                data = json.load(f)
            self._disabled = set(data) if isinstance(data, list) else set()
        except Exception:
            self._disabled = set()
        self._has_disabled_file = os.path.exists(PLUGINS_DISABLED_FILE)

    def _save_disabled(self):
        """Persist disabled plugin IDs to disk."""
        with open(PLUGINS_DISABLED_FILE, "w") as f:
            json.dump(sorted(self._disabled), f)

    def discover(self):
        """Scan plugins directory for valid plugin.json manifests."""
        if not os.path.isdir(PLUGINS_DIR):
            return
        for name in sorted(os.listdir(PLUGINS_DIR)):
            pdir = os.path.join(PLUGINS_DIR, name)
            manifest_path = os.path.join(pdir, "plugin.json")
            if not os.path.isdir(pdir) or not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path) as f:
                    info = json.load(f)
                info["_path"] = pdir
                pid = info.get("id", name)
                self._manifests[pid] = info
            except Exception as e:
                print(f"[Plugin] Failed to read {manifest_path}: {e}")

    def load_all(self, context):
        """Import and instantiate all discovered plugins (skip disabled)."""
        self._context = context
        for pid, info in self._manifests.items():
            # Plugins with default_disabled: true start disabled unless user
            # has explicitly toggled them (i.e. a disabled file exists).
            if info.get("default_disabled") and pid not in self._disabled and not self._has_disabled_file:
                self._disabled.add(pid)
                self._save_disabled()
            if pid in self._disabled:
                print(f"[Plugin] Skipped (disabled): {info.get('name', pid)}")
                continue
            self._load_one(pid, info, context)

    def _load_one(self, pid, info, context):
        """Import and instantiate a single plugin."""
        try:
            self._check_requires(info)
            entry = info.get("entry", "__init__")
            mod_path = os.path.join(info["_path"], entry.replace(".", "/") + ".py")
            spec = importlib.util.spec_from_file_location(f"plugins.{pid}", mod_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"plugins.{pid}"] = mod
            self._loading_pid = pid  # so ctx.register_action_type can tag ownership
            try:
                spec.loader.exec_module(mod)
                instance = mod.Plugin(context)
            finally:
                self._loading_pid = None
            self._instances[pid] = instance
            self._errors.pop(pid, None)
            print(f"[Plugin] Loaded: {info.get('name', pid)} v{info.get('version', '?')}")
            return True
        except Exception as e:
            self._errors[pid] = str(e)
            print(f"[Plugin] Failed to load {pid}: {e}")
            return False

    def _check_requires(self, info):
        """Print warnings for missing dependencies (informational only)."""
        for pkg in info.get("requires", []):
            if not has_requirement(pkg):
                print(f"[Plugin] Warning: '{info.get('id')}' requires '{pkg}' which is not installed")

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def is_disabled(self, pid):
        return pid in self._disabled

    def is_loaded(self, pid):
        return pid in self._instances

    def get_error(self, pid):
        return self._errors.get(pid)

    def disable_plugin(self, pid):
        """Disable a plugin. Calls stop() if running. Takes effect on next restart."""
        self._disabled.add(pid)
        self._save_disabled()
        # Stop the instance if it's running
        inst = self._instances.pop(pid, None)
        if inst:
            if hasattr(inst, "stop"):
                try:
                    inst.stop()
                except Exception:
                    pass
            self._running.pop(pid, None)
            # Remove any action types this plugin registered
            to_remove = [tid for tid, d in self._action_types.items()
                         if getattr(d.get("handler"), "__self__", None) is inst]
            for tid in to_remove:
                del self._action_types[tid]

    def reload_plugin(self, pid):
        """Stop, reimport, and restart a plugin without full app restart."""
        info = self._manifests.get(pid)
        if not info:
            return False
        # Stop the running instance
        inst = self._instances.pop(pid, None)
        if inst:
            if hasattr(inst, "stop"):
                try:
                    inst.stop()
                except Exception:
                    pass
            self._running.pop(pid, None)
            # Remove action types registered by old instance
            to_remove = [tid for tid, d in self._action_types.items()
                         if getattr(d.get("handler"), "__self__", None) is inst]
            for tid in to_remove:
                del self._action_types[tid]
        # Clear cached module so importlib re-reads the source
        mod_key = f"plugins.{pid}"
        sys.modules.pop(mod_key, None)
        # Clear __pycache__ in plugin dir
        cache_dir = os.path.join(info["_path"], "__pycache__")
        if os.path.isdir(cache_dir):
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)
        # Re-load
        if not self._load_one(pid, info, self._context):
            return False
        # Re-start service if applicable (only if not bound to a button on a
        # page that isn't currently showing)
        new_inst = self._instances.get(pid)
        if new_inst:
            ptypes = info.get("type", "")
            if isinstance(ptypes, str):
                ptypes = [ptypes]
            if "service" in ptypes:
                if self._owns_a_button(pid) and pid not in self._bound_plugins_for_page(self._current_page()):
                    pass  # its button is on a different page -- stays off until shown
                else:
                    self._start_pid(pid, new_inst, info)
        return True

    def _current_page(self):
        """Best-effort lookup of the DisplayPad's active page via the stored
        plugin context (defaults to 0 if unavailable)."""
        ctx = getattr(self, "_context", None)
        get_page = getattr(ctx, "get_displaypad_current_page", None)
        return get_page() if callable(get_page) else 0

    def enable_plugin(self, pid):
        """Enable a plugin. Loads it immediately if possible."""
        self._disabled.discard(pid)
        self._save_disabled()
        info = self._manifests.get(pid)
        if info and pid not in self._instances and hasattr(self, "_context"):
            if self._load_one(pid, info, self._context):
                # Start service if applicable
                inst = self._instances.get(pid)
                if inst:
                    ptypes = info.get("type", "")
                    if isinstance(ptypes, str):
                        ptypes = [ptypes]
                    if "service" in ptypes:
                        if self._owns_a_button(pid) and pid not in self._bound_plugins_for_page(self._current_page()):
                            pass
                        else:
                            self._start_pid(pid, inst, info)

    # ── Panel plugins ─────────────────────────────────────────────────────────

    def get_panel_plugins(self):
        """Yield (id, info, instance) for plugins that provide a panel."""
        for pid, inst in self._instances.items():
            info = self._manifests[pid]
            ptypes = info.get("type", "")
            if isinstance(ptypes, str):
                ptypes = [ptypes]
            if "panel" in ptypes and hasattr(inst, "create_panel"):
                yield pid, info, inst

    # ── Action plugins ────────────────────────────────────────────────────────

    def get_action_type_ids(self):
        """Return list of registered plugin action type IDs."""
        return list(self._action_types.keys())

    def get_action_type_labels(self):
        """Return list of (type_id, label) tuples."""
        return [(tid, d["label"]) for tid, d in self._action_types.items()]

    def get_action_handler(self, type_id):
        """Return handler callable for a plugin action type, or None."""
        entry = self._action_types.get(type_id)
        return entry["handler"] if entry else None

    def get_action_value_options(self, type_id):
        """Return (display_label, value) tuples for a plugin action type, or None.

        Plugin callbacks may raise — we swallow exceptions and treat them as
        "no suggestions" so the editor falls back to a plain text entry.
        Returned tuples have both fields as strings so the UI can show them
        directly; bare-string entries from plugins are normalised here.
        """
        entry = self._action_types.get(type_id)
        if not entry:
            return None
        cb = entry.get("value_options")
        if not callable(cb):
            return None
        try:
            opts = cb() or []
        except Exception:
            return None
        result = []
        for o in opts:
            if isinstance(o, (list, tuple)) and len(o) >= 2:
                result.append((str(o[0]), str(o[1])))
            else:
                s = str(o)
                result.append((s, s))
        return result

    # ── DisplayPad page-scoped services ───────────────────────────────────────
    #
    # A service plugin that also registers an action type (e.g. Now Playing,
    # via register_action_type) is "page-bound": it only makes sense to run
    # while a button on the currently visible DisplayPad page has that action
    # type assigned. Such plugins are started/stopped with their normal
    # start()/stop() lifecycle as the user switches pages — no extra hook is
    # required in the plugin interface. A service plugin that registers no
    # action type at all (e.g. a background socket server) is treated as
    # global and simply runs for the whole app lifetime, as before.

    def _owns_a_button(self, pid):
        """True if this plugin registered at least one action type."""
        return any(d.get("owner") == pid for d in self._action_types.values())

    def _bound_plugins_for_page(self, page):
        """Return the set of plugin ids whose registered action type is
        assigned to some button on the given DisplayPad page."""
        from shared.config import _load_displaypad_actions
        actions = _load_displaypad_actions(page)
        assigned = {a.get("type") for a in actions if a.get("type") not in (None, "none")}
        bound = set()
        for tid in assigned:
            entry = self._action_types.get(tid)
            if entry and entry.get("owner"):
                bound.add(entry["owner"])
        return bound

    def _start_pid(self, pid, inst, info, reason=""):
        if not hasattr(inst, "start"):
            return
        try:
            inst.start()
            self._running[pid] = True
            print(f"[Plugin] Started service{reason}: {info.get('name', pid)}")
        except Exception as e:
            print(f"[Plugin] Failed to start {pid}: {e}")

    def _stop_pid(self, pid, inst, info, reason=""):
        if not hasattr(inst, "stop"):
            return
        try:
            inst.stop()
        except Exception:
            pass
        self._running[pid] = False
        print(f"[Plugin] Stopped service{reason}: {info.get('name', pid)}")

    def sync_services_for_page(self, page):
        """Call this whenever the DisplayPad's active page changes. Stops
        page-bound service plugins whose button isn't on the new page and
        starts the ones whose button is — using their own start()/stop()."""
        bound = self._bound_plugins_for_page(page)
        _dbg(f"[DBG PluginManager] sync_services_for_page({page}): bound={bound} "
             f"running={dict(self._running)}")
        for pid, inst in list(self._instances.items()):
            info = self._manifests.get(pid, {})
            ptypes = info.get("type", "")
            if isinstance(ptypes, str):
                ptypes = [ptypes]
            if "service" not in ptypes or not self._owns_a_button(pid):
                continue  # not a service, or a global service -- leave alone
            should_run = pid in bound
            is_running = self._running.get(pid, False)
            _dbg(f"[DBG PluginManager]   {pid}: should_run={should_run} is_running={is_running}")
            if should_run and not is_running:
                self._start_pid(pid, inst, info, f" (page {page})")
            elif not should_run and is_running:
                self._stop_pid(pid, inst, info, f" (button not on page {page})")


    # ── Service lifecycle ─────────────────────────────────────────────────────

    def start_services(self):
        """Call start() on all service-type plugins. A plugin that binds to a
        specific DisplayPad button only starts if that button is on the
        page shown at launch (page 0); it will start later via
        sync_services_for_page() once its page becomes active. A plugin with
        no button binding is global and always starts with the app."""
        for pid, inst in self._instances.items():
            info = self._manifests[pid]
            ptypes = info.get("type", "")
            if isinstance(ptypes, str):
                ptypes = [ptypes]
            if "service" not in ptypes:
                continue
            if self._owns_a_button(pid) and pid not in self._bound_plugins_for_page(0):
                continue
            self._start_pid(pid, inst, info)

    def shutdown(self):
        """Call stop() on all plugins that have it."""
        for pid, inst in self._instances.items():
            if hasattr(inst, "stop"):
                try:
                    inst.stop()
                except Exception:
                    pass
                self._running[pid] = False
