"""Shared configuration paths and load/save helpers for BaseCamp Linux."""
import os
import sys
import json
import pwd as _pwd
from PIL import Image


def _read_json(path):
    with open(path) as f:
        return json.load(f)

# ── Path setup ─────────────────────────────────────────────────────────────────

def _resolve_real_user():
    """Return (home_dir, uid, gid) for the invoking user.

    When running under sudo we honour SUDO_USER, but only if it resolves to a
    real non-root account — protects against a poisoned env var that could
    redirect root's file writes into an arbitrary user's tree.
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            pw = _pwd.getpwnam(sudo_user)
        except KeyError:
            pw = None
        if pw and pw.pw_uid != 0:
            return pw.pw_dir, pw.pw_uid, pw.pw_gid
    return os.path.expanduser("~"), None, None


_real_home, _real_uid, _real_gid = _resolve_real_user()


def _ensure_owned_dir(path):
    """Create a directory and, when running as root, chown it to the invoking user
    so the user can manage their own config outside the app."""
    os.makedirs(path, exist_ok=True)
    if _real_uid is not None and os.geteuid() == 0:
        try:
            st = os.stat(path)
            if st.st_uid != _real_uid:
                os.chown(path, _real_uid, _real_gid)
        except OSError:
            pass


CONFIG_DIR       = os.path.join(_real_home, ".config", "mountain-time-sync")
_ensure_owned_dir(CONFIG_DIR)

STYLE_FILE       = os.path.join(CONFIG_DIR, "style")
BUTTON_FILE      = os.path.join(CONFIG_DIR, "buttons.json")
OBS_FILE         = os.path.join(CONFIG_DIR, "obs.json")
OBS_BACKUP_FILE  = os.path.join(CONFIG_DIR, "obs_backup.json")
MAIN_MODE_FILE   = os.path.join(CONFIG_DIR, "main_display_mode")
AUTOSTART_FILE   = os.path.join(
    _real_home, ".config", "autostart", "basecamp-linux.desktop"
)
SPLASH_FILE      = os.path.join(CONFIG_DIR, "splash")
ZONE_FILE        = os.path.join(CONFIG_DIR, "zone_colors.json")
RGB_FILE         = os.path.join(CONFIG_DIR, "rgb_settings.json")
PER_KEY_FILE     = os.path.join(CONFIG_DIR, "per_key_colors.json")
PRESET_FILE      = os.path.join(CONFIG_DIR, "rgb_presets.json")
ICON_LAST_FILE      = os.path.join(CONFIG_DIR, "icon_last.json")
ICON_LIBRARY_DIR    = os.path.join(CONFIG_DIR, "icon_library")
MAIN_LIBRARY_DIR    = os.path.join(CONFIG_DIR, "main_library")
MAKALU_LED_FILE     = os.path.join(CONFIG_DIR, "makalu_leds.json")
MAKALU_PRESET_FILE  = os.path.join(CONFIG_DIR, "makalu_presets.json")
MAKALU_DPI_FILE     = os.path.join(CONFIG_DIR, "makalu_dpi.json")
MAKALU_REMAP_FILE   = os.path.join(CONFIG_DIR, "makalu_remap.json")
DISPLAYPAD_LIBRARY_DIR     = os.path.join(CONFIG_DIR, "displaypad_library")
DISPLAYPAD_FS_LIBRARY_DIR  = os.path.join(CONFIG_DIR, "displaypad_fs_library")
DISPLAYPAD_BTN_FILE        = os.path.join(CONFIG_DIR, "displaypad_buttons.json")
DISPLAYPAD_FULLSCREEN_FILE = os.path.join(CONFIG_DIR, "displaypad_fullscreen.json")
DISPLAYPAD_ACTIONS_FILE    = os.path.join(CONFIG_DIR, "displaypad_actions.json")
DISPLAYPAD_PAGES_FILE      = os.path.join(CONFIG_DIR, "displaypad_pages.json")
DISPLAYPAD_ROTATION_FILE    = os.path.join(CONFIG_DIR, "displaypad_rotation")
DISPLAYPAD_BRIGHTNESS_FILE  = os.path.join(CONFIG_DIR, "displaypad_brightness")
DISPLAYPAD_DEBOUNCE_FILE    = os.path.join(CONFIG_DIR, "displaypad_debounce")
MACROS_FILE                 = os.path.join(CONFIG_DIR, "macros.json")
MOUSE_RECORDINGS_DIR        = os.path.join(CONFIG_DIR, "mouse_recordings")
LAST_DIRS_FILE              = os.path.join(CONFIG_DIR, "last_dirs.json")
PLUGINS_DIR                 = os.path.join(CONFIG_DIR, "plugins")
PLUGINS_DISABLED_FILE       = os.path.join(CONFIG_DIR, "plugins_disabled.json")
_ensure_owned_dir(PLUGINS_DIR)


def _load_last_dir(kind):
    """Return the last directory used for a given file-picker context, or None.
    kind: free-form key like 'image', 'folder', 'app', 'gif' — caller decides.

    Lookup order:
      1. Saved last directory for this kind (last_dirs.json)
      2. $ICON_PATH environment variable, if set and valid
      3. /usr/share/icons as a sensible Linux default
    """
    try:
        with open(LAST_DIRS_FILE) as f:
            data = json.load(f)
        path = data.get(kind)
        if path and os.path.isdir(path):
            return path
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    env_path = os.environ.get("ICON_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path
    if os.path.isdir("/usr/share/icons"):
        return "/usr/share/icons"
    return None


def reset_last_dirs():
    """Wipe the remembered last-used directory for every file-picker kind.
    Next pickers will fall back to ICON_PATH / /usr/share/icons."""
    try:
        os.remove(LAST_DIRS_FILE)
    except FileNotFoundError:
        pass
    except OSError:
        try:
            with open(LAST_DIRS_FILE, "w") as f:
                json.dump({}, f)
        except OSError:
            pass


def _save_last_dir(kind, path):
    """Remember the directory of a chosen file/folder for next time."""
    if not path:
        return
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if not directory or not os.path.isdir(directory):
        return
    try:
        with open(LAST_DIRS_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    data[kind] = directory
    try:
        with open(LAST_DIRS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass

# ── Auto-copy bundled plugins on first run ───────────────────────────────────

def _bundled_plugin_version(path):
    """Read version string from plugin.json in `path`, or '' on any error."""
    try:
        with open(os.path.join(path, "plugin.json")) as f:
            return str(json.load(f).get("version", ""))
    except Exception:
        return ""


def _plugin_version_tuple(s):
    parts = []
    for p in str(s or "").lstrip("v").split("."):
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts) or (0,)


def _copy_bundled_plugins():
    """Copy bundled example plugins to user plugins dir.

    On first run, all bundled plugins are installed. On subsequent app
    upgrades, any bundled plugin whose version is newer than the installed
    copy is refreshed in place — config.json and other user-state files in
    the plugin dir are preserved, only the plugin's own source files are
    overwritten.
    """
    import shutil
    # Resolve the source dir from our own __file__ so it naturally tracks
    # the source-overlay: if this config.py came from the overlay, the
    # plugins/ it ships sit right next to it and we pick those up. When no
    # overlay is active __file__ points into _internal/, which is exactly
    # where PyInstaller bundles plugins via the datas=[('plugins',...)]
    # entry, so the fallback to _MEIPASS is just defense-in-depth.
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(base, "plugins")) \
            and getattr(sys, "frozen", False):
        base = sys._MEIPASS
    bundled = os.path.join(base, "plugins")
    if not os.path.isdir(bundled):
        return
    for name in os.listdir(bundled):
        src = os.path.join(bundled, name)
        dst = os.path.join(PLUGINS_DIR, name)
        if not os.path.isdir(src):
            continue
        if not os.path.exists(dst):
            shutil.copytree(src, dst)
            print(f"[Plugin] Installed bundled plugin: {name}")
            continue
        src_ver = _bundled_plugin_version(src)
        dst_ver = _bundled_plugin_version(dst)
        if not src_ver or _plugin_version_tuple(src_ver) <= _plugin_version_tuple(dst_ver):
            continue
        # Newer bundled version — overwrite source files but keep user state
        # (config.json, *.json that aren't plugin.json, any *.cache files etc.)
        for src_name in os.listdir(src):
            src_item = os.path.join(src, src_name)
            dst_item = os.path.join(dst, src_name)
            try:
                if os.path.isdir(src_item):
                    if os.path.isdir(dst_item):
                        shutil.rmtree(dst_item)
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)
            except Exception as e:
                print(f"[Plugin] Failed to refresh {name}/{src_name}: {e}")
        print(f"[Plugin] Refreshed bundled plugin: {name} {dst_ver} → {src_ver}")

_copy_bundled_plugins()


# ── Profiles (named action / display config snapshots) ──────────────────────

PROFILES_DIR        = os.path.join(CONFIG_DIR, "profiles")
ACTIVE_PROFILE_FILE = os.path.join(CONFIG_DIR, "active_profile")
_ensure_owned_dir(PROFILES_DIR)

# Files that get snapshotted into a profile — keyboard buttons + DisplayPad
# layout. Library / cache dirs are kept global on purpose so users don't have
# to re-upload the same icons per profile.
_PROFILE_FILES = [
    "buttons.json",
    "obs.json",
    "displaypad_buttons.json",
    "displaypad_fullscreen.json",
    "displaypad_actions.json",
    "displaypad_pages.json",
    "displaypad_rotation",
    "macros.json",
]


def _safe_profile_name(name):
    """Sanitise a profile name: keep alnum, dash, underscore, space."""
    cleaned = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    return cleaned[:48]


def list_profiles():
    """Return sorted list of saved profile names."""
    if not os.path.isdir(PROFILES_DIR):
        return []
    return sorted(
        d for d in os.listdir(PROFILES_DIR)
        if os.path.isdir(os.path.join(PROFILES_DIR, d))
    )


def get_active_profile():
    try:
        with open(ACTIVE_PROFILE_FILE) as f:
            name = f.read().strip()
        if name and os.path.isdir(os.path.join(PROFILES_DIR, name)):
            return name
    except OSError:
        pass
    return ""


def set_active_profile(name):
    try:
        with open(ACTIVE_PROFILE_FILE, "w") as f:
            f.write(name or "")
        if _real_uid is not None and os.geteuid() == 0:
            try:
                os.chown(ACTIVE_PROFILE_FILE, _real_uid, _real_gid)
            except OSError:
                pass
    except OSError:
        pass


def save_profile(name):
    """Snapshot the current configuration into profiles/<name>/."""
    import shutil
    safe = _safe_profile_name(name)
    if not safe:
        raise ValueError("Invalid profile name")
    target = os.path.join(PROFILES_DIR, safe)
    _ensure_owned_dir(target)
    saved = 0
    for fname in _PROFILE_FILES:
        src = os.path.join(CONFIG_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(target, fname))
            saved += 1
    set_active_profile(safe)
    return safe, saved


def load_profile(name):
    """Restore a saved profile back into the live config files."""
    import shutil
    safe = _safe_profile_name(name)
    src_dir = os.path.join(PROFILES_DIR, safe)
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"Profile not found: {safe}")
    restored = 0
    for fname in _PROFILE_FILES:
        src = os.path.join(src_dir, fname)
        if os.path.exists(src):
            dst = os.path.join(CONFIG_DIR, fname)
            shutil.copy2(src, dst)
            if _real_uid is not None and os.geteuid() == 0:
                try:
                    os.chown(dst, _real_uid, _real_gid)
                except OSError:
                    pass
            restored += 1
    set_active_profile(safe)
    return restored


def delete_profile(name):
    import shutil
    safe = _safe_profile_name(name)
    target = os.path.join(PROFILES_DIR, safe)
    if os.path.isdir(target):
        shutil.rmtree(target)
        if get_active_profile() == safe:
            set_active_profile("")
        return True
    return False


# ── Backup / Restore ─────────────────────────────────────────────────────────

# Folders inside CONFIG_DIR that are user-replaceable caches / generated assets
# — excluded from backups to keep ZIPs small. Plugins are also excluded so we
# don't pull in arbitrary third-party code via a backup file.
_BACKUP_EXCLUDE_DIRS = {
    "icon_library", "main_library",
    "displaypad_library", "displaypad_fs_library",
    "mouse_recordings", "plugins",
}


def export_backup(zip_path):
    """Write a ZIP archive containing all small JSON/state config files.
    Large media libraries and plugins are excluded — re-add them manually."""
    import zipfile
    written = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(CONFIG_DIR):
            rel = os.path.relpath(root, CONFIG_DIR)
            # Skip excluded top-level dirs in-place so os.walk doesn't recurse
            parts = [] if rel == "." else rel.split(os.sep)
            if parts and parts[0] in _BACKUP_EXCLUDE_DIRS:
                dirs[:] = []
                continue
            for name in files:
                src = os.path.join(root, name)
                arcname = os.path.relpath(src, CONFIG_DIR)
                try:
                    zf.write(src, arcname)
                    written += 1
                except OSError:
                    pass
    return written


def import_backup(zip_path):
    """Extract a backup ZIP into CONFIG_DIR, overwriting any existing files.
    Refuses paths with .. or absolute components — defends against malicious ZIPs."""
    import zipfile
    restored = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            # Reject path traversal
            if (os.path.isabs(name)
                    or ".." in name.replace("\\", "/").split("/")):
                continue
            target = os.path.join(CONFIG_DIR, name)
            target_dir = os.path.dirname(target)
            # Final guard: make sure resolved target lives under CONFIG_DIR
            if not os.path.realpath(target).startswith(
                    os.path.realpath(CONFIG_DIR) + os.sep):
                continue
            if name.endswith("/"):
                _ensure_owned_dir(target)
                continue
            if target_dir:
                _ensure_owned_dir(target_dir)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            if _real_uid is not None and os.geteuid() == 0:
                try:
                    os.chown(target, _real_uid, _real_gid)
                except OSError:
                    pass
            restored += 1
    return restored


# Keep these for backward compatibility in code that imports them by old names
RGB_PRESETS_FILE = PRESET_FILE


# ── OBS internal order ────────────────────────────────────────────────────────

OBS_INTERNAL_ORDER = ["none", "scene", "record", "stream"]

# ── Style ──────────────────────────────────────────────────────────────────────

def load_config():
    """Load style string. Returns 'analog' if not set."""
    try:
        with open(STYLE_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "analog"


def save_config(style_arg):
    with open(STYLE_FILE, "w") as f:
        f.write(style_arg)


# Keep old names used throughout gui.py
load_style = load_config
save_style = save_config


# ── Buttons ────────────────────────────────────────────────────────────────────

def load_buttons():
    default = [{"icon": 7, "action": "", "type": "shell"} for _ in range(4)]
    try:
        with open(BUTTON_FILE) as f:
            data = json.load(f)
        for i in range(4):
            if i < len(data):
                default[i].update(data[i])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return default


def save_buttons(buttons):
    with open(BUTTON_FILE, "w") as f:
        json.dump(buttons, f, indent=2)


# ── OBS ────────────────────────────────────────────────────────────────────────

def load_obs_config():
    default = {
        "host": "localhost",
        "port": 4455,
        "password": "",
        "buttons": [{"type": "none", "scene": ""} for _ in range(4)],
    }
    try:
        with open(OBS_FILE) as f:
            data = json.load(f)
        for k in ("host", "port", "password"):
            if k in data:
                default[k] = data[k]
        for i in range(4):
            if i < len(data.get("buttons", [])):
                default["buttons"][i].update(data["buttons"][i])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return default


def save_obs_config(cfg):
    with open(OBS_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Autostart ──────────────────────────────────────────────────────────────────

def _autostart_exec():
    _FROZEN = getattr(sys, "frozen", False)
    if _FROZEN:
        p = os.environ.get("APPIMAGE", sys.executable)
        return f'"{p}" --minimized'
    # __file__ would refer to this module; we need the gui entry point.
    # Callers that know the gui path can override; fall back to gui.py sibling.
    gui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gui.py")
    return f'"{sys.executable}" "{gui_path}" --minimized'


def load_autostart_enabled():
    return os.path.exists(AUTOSTART_FILE)


def save_autostart_enabled(val):
    if val:
        os.makedirs(os.path.dirname(AUTOSTART_FILE), exist_ok=True)
        with open(AUTOSTART_FILE, "w") as f:
            f.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=BaseCamp Linux\n"
                "Comment=Mountain Everest Max display control\n"
                f"Exec={_autostart_exec()}\n"
                "Icon=basecamp-linux\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
    else:
        try:
            os.remove(AUTOSTART_FILE)
        except FileNotFoundError:
            pass


# ── Splash ─────────────────────────────────────────────────────────────────────

def load_splash_enabled():
    try:
        with open(SPLASH_FILE) as f:
            return f.read().strip() != "0"
    except FileNotFoundError:
        return True


def save_splash_enabled(val):
    with open(SPLASH_FILE, "w") as f:
        f.write("1" if val else "0")


# ── RGB zone colors ────────────────────────────────────────────────────────────

def load_zone_colors(defaults):
    """Load zone color dict and brightness from ZONE_FILE.
    Returns (colors_dict, brightness_int)."""
    try:
        data = _read_json(ZONE_FILE)
        colors = dict(defaults)
        for k in colors:
            if k in data and len(data[k]) == 3:
                colors[k] = tuple(data[k])
        brightness = int(data.get("brightness", 100))
        return colors, brightness
    except Exception:
        return dict(defaults), 100


# Keep old name used in gui.py
load_zone_config = load_zone_colors


def save_zone_colors(colors, brightness):
    data = {k: list(v) for k, v in colors.items()}
    data["brightness"] = brightness
    with open(ZONE_FILE, "w") as f:
        f.write(json.dumps(data, indent=2))


# Keep old name used in gui.py
save_zone_config = save_zone_colors


# ── RGB effect settings ────────────────────────────────────────────────────────

def load_rgb_settings():
    try:
        return _read_json(RGB_FILE)
    except Exception:
        return {}


# Keep old name used in gui.py
load_rgb_config = load_rgb_settings


def save_rgb_settings(data):
    with open(RGB_FILE, "w") as f:
        f.write(json.dumps(data, indent=2))


# Keep old name used in gui.py
save_rgb_config = save_rgb_settings


# ── Per-key RGB ────────────────────────────────────────────────────────────────

_SIDE_ZONE_INDICES = [
    [13, 14, 15, 7, 6, 5, 4, 3, 2, 1, 0],             # main top   (11)
    [9, 8, 10, 11],                                     # main right  (4)
    [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 12],  # main bottom(12)
    [16, 17, 18, 19],                                   # main left   (4)
    [31, 44, 43, 42],                                   # np top      (4)
    [41, 40, 39],                                       # np right    (3)
    [35, 36, 37, 38],                                   # np bottom   (4)
    [32, 33, 34],                                       # np left     (3)
]


def _load_per_key():
    default_side = [(255, 255, 255)] * 45
    try:
        d = _read_json(PER_KEY_FILE)
        leds = [tuple(c) for c in d.get("leds", [])]
        leds = (leds + [(20, 20, 20)] * 126)[:126]
        raw = d.get("side", [])
        if isinstance(raw, list) and len(raw) == 45:
            side = [tuple(c) for c in raw]
        elif isinstance(raw, dict):
            # backward compat: zone dict → expand to 45
            side = list(default_side)
            zone_map = {
                "Top":    _SIDE_ZONE_INDICES[0], "Right":  _SIDE_ZONE_INDICES[1],
                "Bottom": _SIDE_ZONE_INDICES[2], "Left":   _SIDE_ZONE_INDICES[3],
                "NP": _SIDE_ZONE_INDICES[4] + _SIDE_ZONE_INDICES[5] +
                      _SIDE_ZONE_INDICES[6] + _SIDE_ZONE_INDICES[7],
            }
            for z, idxs in zone_map.items():
                c = tuple(raw.get(z, (255, 255, 255)))
                for i in idxs:
                    side[i] = c
        else:
            side = list(default_side)
        bri = int(d.get("brightness", 100))
        return leds, side, bri
    except Exception:
        return [(20, 20, 20)] * 126, list(default_side), 100


def _save_per_key(leds, side, bri):
    with open(PER_KEY_FILE, "w") as f:
        f.write(json.dumps({
            "leds": [list(c) for c in leds],
            "side": [list(c) for c in side],
            "brightness": bri,
        }, indent=2))


# ── Presets ────────────────────────────────────────────────────────────────────

def _load_presets():
    _HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _FROZEN = getattr(sys, "frozen", False)
    _RES = getattr(sys, "_MEIPASS", _HERE) if _FROZEN else _HERE
    defaults = {}
    _default_file = os.path.join(_RES, "default_presets.json")
    try:
        defaults = _read_json(_default_file)
    except Exception:
        pass
    try:
        user = _read_json(PRESET_FILE)
        defaults.update(user)
    except Exception:
        pass
    return defaults


def _save_presets(presets):
    with open(PRESET_FILE, "w") as f:
        f.write(json.dumps(presets, indent=2))


# ── Everest 60 per-key storage ─────────────────────────────────────────────────

PER_KEY_60_FILE = os.path.join(CONFIG_DIR, "per_key_60_colors.json")
PRESET_60_FILE  = os.path.join(CONFIG_DIR, "rgb60_presets.json")


def _load_per_key_60():
    try:
        d = _read_json(PER_KEY_60_FILE)
        leds = [tuple(c) for c in d.get("leds", [])]
        leds = (leds + [(20, 20, 20)] * 64)[:64]
        bri  = int(d.get("brightness", 100))
        return leds, [], bri
    except Exception:
        return [(20, 20, 20)] * 64, [], 100


def _save_per_key_60(leds, _side, bri):
    with open(PER_KEY_60_FILE, "w") as f:
        f.write(json.dumps({
            "leds": [list(c) for c in leds],
            "brightness": bri,
        }, indent=2))


def _load_presets_60():
    _HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _FROZEN = getattr(sys, "frozen", False)
    _RES = getattr(sys, "_MEIPASS", _HERE) if _FROZEN else _HERE
    defaults = {}
    try:
        defaults = _read_json(os.path.join(_RES, "default_presets_60.json"))
    except Exception:
        pass
    try:
        user = _read_json(PRESET_60_FILE)
        defaults.update(user)
    except Exception:
        pass
    return defaults


def _save_presets_60(presets):
    with open(PRESET_60_FILE, "w") as f:
        f.write(json.dumps(presets, indent=2))


# ── Makalu 67 LED storage ───────────────────────────────────────────────────────

def _load_makalu_leds():
    try:
        d = _read_json(MAKALU_LED_FILE)
        leds = [tuple(c) for c in d.get("leds", [])]
        leds = (leds + [(255, 255, 255)] * 8)[:8]
        bri    = int(d.get("brightness", 100))
        preset = d.get("preset", "")
        return leds, bri, preset
    except Exception:
        return [(255, 255, 255)] * 8, 100, ""


def _save_makalu_leds(leds, bri, preset=""):
    with open(MAKALU_LED_FILE, "w") as f:
        f.write(json.dumps({"leds": [list(c) for c in leds], "brightness": bri, "preset": preset}))


def _load_makalu_presets():
    _HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _FROZEN = getattr(sys, "frozen", False)
    _RES = getattr(sys, "_MEIPASS", _HERE) if _FROZEN else _HERE
    defaults = {}
    try:
        defaults = _read_json(os.path.join(_RES, "default_makalu_presets.json"))
    except Exception:
        pass
    try:
        user = _read_json(MAKALU_PRESET_FILE)
        defaults.update(user)
    except Exception:
        pass
    return defaults


def _save_makalu_presets(presets):
    with open(MAKALU_PRESET_FILE, "w") as f:
        f.write(json.dumps(presets, indent=2))


DPI_DEFAULTS = [400, 800, 1600, 3200, 6400]


def _load_makalu_dpi():
    try:
        d = _read_json(MAKALU_DPI_FILE)
        values = [int(v) for v in d.get("levels", DPI_DEFAULTS)]
        if len(values) == 5:
            return values
    except Exception:
        pass
    return list(DPI_DEFAULTS)


def _save_makalu_dpi(levels):
    with open(MAKALU_DPI_FILE, "w") as f:
        f.write(json.dumps({"levels": levels}))


REMAP_DEFAULTS = {"1": "left", "2": "right", "3": "middle",
                  "4": "back", "5": "forward", "6": "dpi+"}

REMAP_DEFAULTS_MAX = {"1": "left", "2": "right", "3": "middle",
                      "4": "dpi+", "5": "disabled", "6": "disabled",
                      "7": "forward", "8": "back"}


def _load_makalu_remap(defaults=None):
    if defaults is None:
        defaults = REMAP_DEFAULTS
    try:
        d = _read_json(MAKALU_REMAP_FILE)
        result = dict(defaults)
        result.update({k: v for k, v in d.items() if k in defaults})
        return result
    except Exception:
        return dict(defaults)


def _save_makalu_remap(assignments):
    with open(MAKALU_REMAP_FILE, "w") as f:
        f.write(json.dumps(assignments))


# ── DisplayPad config ────────────────────────────────────────────────────────

def _load_displaypad_buttons():
    """Return dict {str(key_idx): image_path} for DisplayPad button images."""
    try:
        return _read_json(DISPLAYPAD_BTN_FILE)
    except Exception:
        return {}


def _save_displaypad_buttons(data):
    with open(DISPLAYPAD_BTN_FILE, "w") as f:
        f.write(json.dumps(data))


def _load_displaypad_fullscreen():
    try:
        return _read_json(DISPLAYPAD_FULLSCREEN_FILE).get("gif_path")
    except Exception:
        return None


def _save_displaypad_fullscreen(path):
    with open(DISPLAYPAD_FULLSCREEN_FILE, "w") as f:
        f.write(json.dumps({"gif_path": path}))


def _clear_displaypad_fullscreen():
    try:
        os.remove(DISPLAYPAD_FULLSCREEN_FILE)
    except Exception:
        pass


def _load_displaypad_actions():
    """Return list of 12 dicts with 'type' and 'action' keys."""
    default = [{"type": "none", "action": ""} for _ in range(12)]
    try:
        data = _read_json(DISPLAYPAD_ACTIONS_FILE)
        for i in range(12):
            if i < len(data):
                default[i].update(data[i])
    except Exception:
        pass
    return default


def _save_displaypad_actions(actions):
    with open(DISPLAYPAD_ACTIONS_FILE, "w") as f:
        json.dump(actions, f, indent=2)


def _load_displaypad_pages():
    """Return dict {str(page_num): {buttons: {}, actions: [...], fullscreen: None}}."""
    try:
        return _read_json(DISPLAYPAD_PAGES_FILE)
    except Exception:
        return {}


def _save_displaypad_pages(data):
    with open(DISPLAYPAD_PAGES_FILE, "w") as f:
        json.dump(data, f, indent=2)



def _load_displaypad_rotation():
    try:
        with open(DISPLAYPAD_ROTATION_FILE) as f:
            v = int(f.read().strip())
        return v if v in (0, 90, 180, 270) else 0
    except Exception:
        return 0


def _save_displaypad_rotation(deg):
    with open(DISPLAYPAD_ROTATION_FILE, "w") as f:
        f.write(str(deg))


def _load_displaypad_brightness():
    try:
        with open(DISPLAYPAD_BRIGHTNESS_FILE) as f:
            v = int(f.read().strip())
        return v if v in (0, 25, 50, 75, 100) else 100
    except Exception:
        return 100


def _save_displaypad_brightness(val):
    with open(DISPLAYPAD_BRIGHTNESS_FILE, "w") as f:
        f.write(str(val))


_DEBOUNCE_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]

def _load_displaypad_debounce():
    try:
        with open(DISPLAYPAD_DEBOUNCE_FILE) as f:
            v = float(f.read().strip())
        return v if v in _DEBOUNCE_VALUES else 0.8
    except Exception:
        return 0.8


def _save_displaypad_debounce(val):
    with open(DISPLAYPAD_DEBOUNCE_FILE, "w") as f:
        f.write(str(val))


# ── DisplayPad library helpers ────────────────────────────────────────────────

def _save_to_dp_library(path, gif_frame=0):
    """Resize image to 102×102, save as PNG by content-hash. Returns filename or None."""
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((102, 102), Image.LANCZOS)
        buf = img.tobytes()
        h = hashlib.md5(buf).hexdigest()[:16]
        os.makedirs(DISPLAYPAD_LIBRARY_DIR, exist_ok=True)
        out = os.path.join(DISPLAYPAD_LIBRARY_DIR, f"{h}.png")
        if not os.path.exists(out):
            img.save(out, "PNG")
        return f"{h}.png"
    except Exception:
        return None


def _list_dp_library():
    """Return sorted list of PNG filenames in the DisplayPad library."""
    try:
        return sorted(f for f in os.listdir(DISPLAYPAD_LIBRARY_DIR) if f.endswith(".png"))
    except FileNotFoundError:
        return []


def _compute_dp_lib_hash(path, gif_frame=0):
    """Return the library filename (hash.png) for an image without saving it."""
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((102, 102), Image.LANCZOS)
        h = hashlib.md5(img.tobytes()).hexdigest()[:16]
        return f"{h}.png"
    except Exception:
        return None


def _save_to_dp_fs_library(path):
    """Save fullscreen image/GIF to the DisplayPad fullscreen library. Returns filename or None."""
    import hashlib, shutil
    try:
        os.makedirs(DISPLAYPAD_FS_LIBRARY_DIR, exist_ok=True)
        with open(path, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()[:16]
        ext = os.path.splitext(path)[1].lower() or ".png"
        out = os.path.join(DISPLAYPAD_FS_LIBRARY_DIR, f"{h}{ext}")
        if not os.path.exists(out):
            shutil.copy2(path, out)
        return f"{h}{ext}"
    except Exception:
        return None


def _list_dp_fs_library():
    """Return sorted list of image filenames in the DisplayPad fullscreen library."""
    try:
        return sorted(f for f in os.listdir(DISPLAYPAD_FS_LIBRARY_DIR)
                       if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")))
    except FileNotFoundError:
        return []


# ── Icon library helpers ────────────────────────────────────────────────────────

def _load_icon_last():
    """Return dict {slot_str: thumb_filename} for last uploaded image per slot."""
    try:
        return _read_json(ICON_LAST_FILE)
    except Exception:
        return {}


def _save_icon_last(slot, filename):
    data = _load_icon_last()
    data[str(slot)] = filename
    with open(ICON_LAST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _save_to_library(path, gif_frame=0):
    """Resize image to 72×72, save as PNG by content-hash. Returns filename or None."""
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((72, 72), Image.LANCZOS)
        buf = img.tobytes()
        h = hashlib.md5(buf).hexdigest()[:16]
        os.makedirs(ICON_LIBRARY_DIR, exist_ok=True)
        out = os.path.join(ICON_LIBRARY_DIR, f"{h}.png")
        if not os.path.exists(out):
            img.save(out, "PNG")
        return f"{h}.png"
    except Exception:
        return None


def _save_to_main_library(path, gif_frame=0):
    """Save 96×82 thumbnail of main display image to main_library. Returns filename or None."""
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((96, 82), Image.LANCZOS)
        buf = img.tobytes()
        h = hashlib.md5(buf).hexdigest()[:16]
        os.makedirs(MAIN_LIBRARY_DIR, exist_ok=True)
        out = os.path.join(MAIN_LIBRARY_DIR, f"{h}.png")
        if not os.path.exists(out):
            img.save(out, "PNG")
        return f"{h}.png"
    except Exception:
        return None


def _compute_lib_hash(path, gif_frame=0):
    """Return the library filename (hash.png) for an image without saving it."""
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((72, 72), Image.LANCZOS)
        h = hashlib.md5(img.tobytes()).hexdigest()[:16]
        return f"{h}.png"
    except Exception:
        return None


def _compute_main_lib_hash(path, gif_frame=0):
    import hashlib
    try:
        img = Image.open(path)
        try:
            img.seek(gif_frame)
        except Exception:
            pass
        img = img.convert("RGB").resize((96, 82), Image.LANCZOS)
        h = hashlib.md5(img.tobytes()).hexdigest()[:16]
        return f"{h}.png"
    except Exception:
        return None


def _list_library():
    """Return sorted list of PNG filenames in the icon library."""
    try:
        return sorted(f for f in os.listdir(ICON_LIBRARY_DIR) if f.endswith(".png"))
    except FileNotFoundError:
        return []


def _list_main_library():
    try:
        return sorted(f for f in os.listdir(MAIN_LIBRARY_DIR) if f.endswith(".png"))
    except FileNotFoundError:
        return []


# ── Macros ─────────────────────────────────────────────────────────────────────

def load_macros():
    """Return full macros dict: {"macros": {uuid: {name, actions, repeat_mode, repeat_count}}}."""
    try:
        return _read_json(MACROS_FILE)
    except Exception:
        return {"macros": {}}


def save_macros(data):
    with open(MACROS_FILE, "w") as f:
        json.dump(data, f, indent=2)
