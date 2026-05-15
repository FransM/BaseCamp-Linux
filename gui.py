#!/usr/bin/env python3
"""BaseCamp Linux — multi-device hub GUI."""
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
import subprocess
import datetime
import re
import time
import sys
import os
import json
import math
import colorsys
import psutil
import pwd as _pwd

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_HERE   = os.path.dirname(os.path.abspath(__file__))
_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    _BIN = os.path.dirname(sys.executable)
    _RES = sys._MEIPASS
    PYTHON = None
    SCRIPT = os.path.join(_BIN, "basecamp-controller")
    TRAY_HELPER = os.path.join(_BIN, "basecamp-tray")
else:
    _BIN = _HERE
    _RES = _HERE
    PYTHON = sys.executable
    SCRIPT = os.path.join(_HERE, "mountain-time-sync.py")
    TRAY_HELPER = os.path.join(_HERE, "tray_helper.py")

LANG_DIR = os.path.join(_RES, "lang")

STYLES = {"Analog": "analog", "Digital": "digital"}

# ── Shared modules ─────────────────────────────────────────────────────────────

from shared.config import (
    _real_home, CONFIG_DIR,
    STYLE_FILE, BUTTON_FILE, OBS_FILE, OBS_BACKUP_FILE, MAIN_MODE_FILE,
    AUTOSTART_FILE, SPLASH_FILE, ZONE_FILE, RGB_FILE, PRESET_FILE,
    ICON_LAST_FILE, ICON_LIBRARY_DIR, MAIN_LIBRARY_DIR,
    RGB_PRESETS_FILE,
    load_config, save_config,
    load_style, save_style,
    load_buttons, save_buttons,
    load_obs_config, save_obs_config,
    load_autostart_enabled, save_autostart_enabled,
    load_splash_enabled, save_splash_enabled,
    load_zone_config, save_zone_config, load_zone_colors, save_zone_colors,
    load_rgb_settings, save_rgb_settings,
    load_rgb_config, save_rgb_config,
    _load_per_key, _save_per_key,
    _load_presets, _save_presets,
    _load_icon_last, _save_icon_last,
    _save_to_library, _save_to_main_library,
    _compute_lib_hash, _compute_main_lib_hash,
    _list_library, _list_main_library,
    OBS_INTERNAL_ORDER,
)
from shared.image_utils import image_to_rgb565
from shared.ui_helpers import (
    BG, BG2, BG3, FG, FG2, BLUE, YLW, GRN, RED, BORDER,
    FONT, FONT_BOLD, FONT_SM, FONT_LG,
    ANIM_STEPS, ANIM_MS,
    _rgb_hex, _run_as_sudouser,
    native_open_image, native_open_folder, parse_desktop_apps,
    ColorPickerDialog, pick_color,
    LibraryPickerDialog, pick_library_image, pick_main_library_image,
    MultiUploadDialog,
    CustomRGBWindow,
    AccordionSection,
    _KB_LAYOUT, _KB_CANVAS_W, _KB_CANVAS_H, _SIDE_SZ, _SIDE_OFFSET,
    _QUICK_COLORS, _SIDE_ZONE_INDICES,
    _KB60_LAYOUT, _KB60_CANVAS_W, _KB60_CANVAS_H, _KB60_NUM_LEDS,
)
from devices.everest_max.panel import EverestMaxPanel
from devices.everest60.panel import Everest60Panel
from devices.makalu67.panel import Makalu67Panel
from devices.displaypad.panel import DisplayPadPanel
from devices.obs.panel import OBSPanel
from devices.macros.panel import MacroPanel
from devices.plugins.panel import PluginManagerPanel
from shared.plugins import PluginManager
from shared.plugin_api import PluginContext

# ── Keep backward-compatible module-level names used by existing code ──────────

# These were previously defined at module level in gui.py; keep them so that
# any code that imports gui directly still works.
_AUTOSTART_FILE = AUTOSTART_FILE


def _cmd(*args):
    """Build subprocess command for Everest Max controller."""
    if _FROZEN:
        return [SCRIPT] + list(args)
    return [PYTHON, SCRIPT] + list(args)


def load_lang(code):
    path = os.path.join(LANG_DIR, f"{code}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            with open(os.path.join(LANG_DIR, "de.json"), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


def available_langs():
    result = {}
    try:
        for fname in os.listdir(LANG_DIR):
            if fname.endswith(".json"):
                code = fname[:-5]
                try:
                    with open(os.path.join(LANG_DIR, fname), encoding="utf-8") as f:
                        data = json.load(f)
                    result[code] = data.get("name", code)
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return result


# USB presence detection helpers (non-blocking, best-effort)

def _check_usb_presence(vid, pid):
    """Return True if a USB device with given VID:PID is present.
    Reads /sys/bus/usb/devices/ directly — no subprocess, no forking.
    """
    try:
        target_vid = f"{vid:04x}"
        target_pid = f"{pid:04x}"
        for entry in os.listdir("/sys/bus/usb/devices/"):
            base = f"/sys/bus/usb/devices/{entry}"
            try:
                with open(f"{base}/idVendor") as f:
                    if f.read().strip() != target_vid:
                        continue
                with open(f"{base}/idProduct") as f:
                    if f.read().strip() == target_pid:
                        return True
            except OSError:
                continue
        return False
    except OSError:
        return False


# ── Settings dialog ────────────────────────────────────────────────────────────

class SettingsDialog(ctk.CTkToplevel):
    """Modal with Profiles, Backup/Restore + version info."""
    def __init__(self, app):
        super().__init__(app)
        self._app = app
        self.title(app.T("settings_title"))
        self.geometry("420x580")
        self.resizable(False, False)
        try:
            self.transient(app)
        except Exception:
            pass

        ctk.CTkLabel(self, text=app.T("settings_title"),
                     font=("Helvetica", 14, "bold")).pack(pady=(14, 4))
        ctk.CTkLabel(self, text=f"BaseCamp Linux v{APP_VERSION}",
                     font=("Helvetica", 10), text_color=FG2).pack(pady=(0, 12))

        # ── Profiles section ──
        from shared.config import list_profiles, get_active_profile
        ctk.CTkLabel(self, text=app.T("settings_profiles"),
                     font=("Helvetica", 11, "bold")).pack(pady=(0, 4))

        profile_row = ctk.CTkFrame(self, fg_color="transparent")
        profile_row.pack(fill="x", padx=20, pady=2)
        profiles = list_profiles()
        active   = get_active_profile()
        self._profile_combo = ctk.CTkComboBox(
            profile_row, values=profiles or [app.T("settings_profile_none")],
            width=200, height=30, font=("Helvetica", 11),
            fg_color=BG2, button_color=BLUE, text_color=FG)
        if active and active in profiles:
            self._profile_combo.set(active)
        elif profiles:
            self._profile_combo.set(profiles[0])
        else:
            self._profile_combo.set(app.T("settings_profile_none"))
        self._profile_combo.pack(side="left", padx=(0, 4), fill="x", expand=True)
        ctk.CTkButton(profile_row, text=app.T("settings_profile_load"),
                      width=70, height=30, command=self._do_load_profile).pack(
            side="left", padx=2)
        ctk.CTkButton(profile_row, text=app.T("settings_profile_delete"),
                      width=70, height=30, fg_color=RED, hover_color="#8a1f1f",
                      command=self._do_delete_profile).pack(side="left", padx=2)

        save_row = ctk.CTkFrame(self, fg_color="transparent")
        save_row.pack(fill="x", padx=20, pady=(2, 12))
        self._new_profile_var = ctk.StringVar()
        ctk.CTkEntry(save_row, textvariable=self._new_profile_var,
                     placeholder_text=app.T("settings_profile_name_hint"),
                     height=30, font=("Helvetica", 11),
                     fg_color=BG2, text_color=FG).pack(
            side="left", padx=(0, 4), fill="x", expand=True)
        ctk.CTkButton(save_row, text=app.T("settings_profile_save"),
                      width=70, height=30, command=self._do_save_profile).pack(
            side="left", padx=2)

        # ── Backup / Restore section ──
        ctk.CTkLabel(self, text=app.T("settings_backup_section"),
                     font=("Helvetica", 11, "bold")).pack(pady=(8, 4))
        ctk.CTkButton(self, text=app.T("settings_backup"),
                      command=self._do_backup, height=34, corner_radius=6).pack(
            fill="x", padx=20, pady=4)
        ctk.CTkButton(self, text=app.T("settings_restore"),
                      command=self._do_restore, height=34, corner_radius=6,
                      fg_color=BG3, hover_color=BG2).pack(fill="x", padx=20, pady=4)

        # ── File pickers section ──
        ctk.CTkLabel(self, text=app.T("settings_picker_section"),
                     font=("Helvetica", 11, "bold")).pack(pady=(10, 2))
        ctk.CTkLabel(self, text=app.T("settings_picker_reset_hint"),
                     font=("Helvetica", 9), text_color=FG2,
                     wraplength=380, justify="left").pack(padx=20, pady=(0, 4))
        ctk.CTkButton(self, text=app.T("settings_picker_reset"),
                      command=self._do_reset_pickers, height=30,
                      corner_radius=6, fg_color=BG3, hover_color=BG2).pack(
            fill="x", padx=20, pady=2)

        self._status = ctk.CTkLabel(self, text="", font=("Helvetica", 10),
                                     text_color=FG2)
        self._status.pack(pady=(12, 4))

        # Update-check status (filled in by App.check_for_update if newer found)
        self._update_lbl = ctk.CTkLabel(self, text=getattr(app, "_update_message", ""),
                                         font=("Helvetica", 10), text_color=GRN,
                                         wraplength=380, justify="left")
        self._update_lbl.pack(pady=(0, 4), padx=12)

        # In-app self-update — AppImage only. The button is only created when
        # an AppImage install was detected AND a download URL was resolved.
        self._update_btn = None
        if (getattr(app, "_update_install_type", "") == "appimage"
                and getattr(app, "_update_url", "")):
            self._update_btn = ctk.CTkButton(
                self, text=app.T("settings_update_button"),
                command=self._do_update, height=32, corner_radius=6,
                fg_color=GRN, hover_color="#1f7a3a")
            self._update_btn.pack(pady=(2, 12), padx=20, fill="x")

    def _refresh_profile_combo(self):
        from shared.config import list_profiles, get_active_profile
        profiles = list_profiles()
        self._profile_combo.configure(
            values=profiles or [self._app.T("settings_profile_none")])
        active = get_active_profile()
        if active and active in profiles:
            self._profile_combo.set(active)
        elif profiles:
            self._profile_combo.set(profiles[0])
        else:
            self._profile_combo.set(self._app.T("settings_profile_none"))

    def _do_save_profile(self):
        name = (self._new_profile_var.get() or "").strip()
        if not name:
            self._status.configure(
                text=self._app.T("settings_profile_no_name"), text_color=RED)
            return
        from shared.config import save_profile
        try:
            safe, count = save_profile(name)
            self._new_profile_var.set("")
            self._refresh_profile_combo()
            self._status.configure(
                text=self._app.T("settings_profile_saved", name=safe, n=count),
                text_color=GRN)
        except Exception as e:
            self._status.configure(
                text=self._app.T("settings_profile_err", err=str(e)[:60]),
                text_color=RED)

    def _do_load_profile(self):
        name = self._profile_combo.get()
        from shared.config import load_profile, list_profiles
        if name not in list_profiles():
            return
        from tkinter import messagebox
        if not messagebox.askyesno(
                self._app.T("settings_profiles"),
                self._app.T("settings_profile_load_confirm", name=name),
                parent=self):
            return
        try:
            count = load_profile(name)
            self._status.configure(
                text=self._app.T("settings_profile_loaded", name=name, n=count),
                text_color=GRN)
        except Exception as e:
            self._status.configure(
                text=self._app.T("settings_profile_err", err=str(e)[:60]),
                text_color=RED)

    def _do_delete_profile(self):
        name = self._profile_combo.get()
        from shared.config import delete_profile, list_profiles
        if name not in list_profiles():
            return
        from tkinter import messagebox
        if not messagebox.askyesno(
                self._app.T("settings_profiles"),
                self._app.T("settings_profile_delete_confirm", name=name),
                parent=self):
            return
        delete_profile(name)
        self._refresh_profile_combo()
        self._status.configure(
            text=self._app.T("settings_profile_deleted", name=name),
            text_color=FG2)

    def _do_reset_pickers(self):
        from shared.config import reset_last_dirs
        reset_last_dirs()
        self._status.configure(
            text=self._app.T("settings_picker_reset_ok"), text_color=GRN)

    def _do_backup(self):
        from tkinter import filedialog
        from shared.config import export_backup, _load_last_dir, _save_last_dir
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".zip",
            initialdir=_load_last_dir("backup") or os.path.expanduser("~"),
            initialfile=f"basecamp-backup-{ts}.zip",
            filetypes=[("ZIP", "*.zip")],
            title=self._app.T("settings_backup"))
        if not path:
            return
        _save_last_dir("backup", path)
        try:
            count = export_backup(path)
            self._status.configure(
                text=self._app.T("settings_backup_ok", n=count), text_color=GRN)
        except Exception as e:
            self._status.configure(
                text=self._app.T("settings_backup_err", err=str(e)[:60]),
                text_color=RED)

    def _do_restore(self):
        from tkinter import filedialog, messagebox
        from shared.config import import_backup, _load_last_dir, _save_last_dir
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=_load_last_dir("backup") or os.path.expanduser("~"),
            filetypes=[("ZIP", "*.zip"), ("All", "*.*")],
            title=self._app.T("settings_restore"))
        if not path:
            return
        _save_last_dir("backup", path)
        if not messagebox.askyesno(
                self._app.T("settings_restore"),
                self._app.T("settings_restore_confirm"), parent=self):
            return
        try:
            count = import_backup(path)
            self._status.configure(
                text=self._app.T("settings_restore_ok", n=count), text_color=GRN)
        except Exception as e:
            self._status.configure(
                text=self._app.T("settings_restore_err", err=str(e)[:60]),
                text_color=RED)

    def _do_update(self):
        """Trigger the shared App-level download. UI updates land in our
        local status label / button via the callbacks."""
        app = self._app
        if not getattr(app, "_update_url", "") or not os.environ.get("APPIMAGE"):
            self._status.configure(
                text=app.T("settings_update_no_asset"), text_color=RED)
            return
        if self._update_btn is not None:
            self._update_btn.configure(state="disabled")
        app.run_update_download(
            on_progress=lambda pct: self._status.configure(
                text=app.T("settings_update_downloading", pct=pct), text_color=GRN),
            on_installing=lambda: self._status.configure(
                text=app.T("settings_update_installing"), text_color=GRN),
            on_done=self._on_update_done,
            on_error=self._on_update_error,
        )

    def _on_update_done(self):
        app = self._app
        self._status.configure(text=app.T("settings_update_done"), text_color=GRN)
        if self._update_btn is not None:
            self._update_btn.configure(
                text=app.T("settings_update_restart"),
                state="normal", command=app.restart_after_update,
                fg_color=BLUE, hover_color="#1d4f86")

    def _on_update_error(self, err):
        app = self._app
        self._status.configure(
            text=app.T("settings_update_error", err=err), text_color=RED)
        if self._update_btn is not None:
            self._update_btn.configure(state="normal")


# ── Update-available popup ─────────────────────────────────────────────────────

class UpdateAvailableDialog(ctk.CTkToplevel):
    """Shown once per session when a newer AppImage release is detected.
    Lets the user kick off the download right from the popup so they don't
    have to dig through the settings dialog to find it."""
    def __init__(self, app):
        super().__init__(app)
        self._app = app
        self.title(app.T("update_dialog_title"))
        self.geometry("420x210")
        self.resizable(False, False)
        try:
            self.transient(app)
        except Exception:
            pass

        ctk.CTkLabel(self, text=app.T("update_dialog_title"),
                     font=("Helvetica", 14, "bold")).pack(pady=(16, 4))
        ctk.CTkLabel(self,
                     text=app.T("update_dialog_body",
                                ver=getattr(app, "_update_version", "")),
                     font=("Helvetica", 11), wraplength=380,
                     justify="center").pack(pady=(0, 6), padx=12)

        self._status = ctk.CTkLabel(self, text="", font=("Helvetica", 10),
                                     text_color=FG2, wraplength=380, justify="center")
        self._status.pack(pady=(0, 6))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=(4, 12))
        self._cancel_btn = ctk.CTkButton(
            btns, text=app.T("update_dialog_cancel"), width=130, height=32,
            corner_radius=6, fg_color=BG3, hover_color=BG2,
            command=self.destroy)
        self._cancel_btn.pack(side="left", padx=8)
        self._update_btn = ctk.CTkButton(
            btns, text=app.T("settings_update_button"), width=160, height=32,
            corner_radius=6, fg_color=GRN, hover_color="#1f7a3a",
            command=self._do_update)
        self._update_btn.pack(side="left", padx=8)

    def _do_update(self):
        app = self._app
        if not getattr(app, "_update_url", "") or not os.environ.get("APPIMAGE"):
            self._status.configure(
                text=app.T("settings_update_no_asset"), text_color=RED)
            return
        self._update_btn.configure(state="disabled")
        self._cancel_btn.configure(state="disabled")
        app.run_update_download(
            on_progress=lambda pct: self._status.configure(
                text=app.T("settings_update_downloading", pct=pct), text_color=GRN),
            on_installing=lambda: self._status.configure(
                text=app.T("settings_update_installing"), text_color=GRN),
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def _on_done(self):
        app = self._app
        self._status.configure(text=app.T("settings_update_done"), text_color=GRN)
        self._update_btn.configure(
            text=app.T("settings_update_restart"), state="normal",
            command=app.restart_after_update, fg_color=BLUE,
            hover_color="#1d4f86")
        self._cancel_btn.configure(state="normal")

    def _on_error(self, err):
        app = self._app
        self._status.configure(
            text=app.T("settings_update_error", err=err), text_color=RED)
        self._update_btn.configure(state="normal")
        self._cancel_btn.configure(state="normal")


# ── App ────────────────────────────────────────────────────────────────────────

APP_VERSION = "2.0"


class App(ctk.CTk):
    # VID/PID constants for supported devices
    EVEREST_MAX_VID     = 0x3282
    EVEREST_MAX_PID     = 0x0001
    EVEREST60_VID       = 0x3282
    EVEREST60_PID_ANSI  = 0x0005
    EVEREST60_PID_ISO   = 0x0006
    MAKALU67_VID        = 0x3282
    MAKALU67_PID        = 0x0003
    DISPLAYPAD_VID      = 0x3282
    DISPLAYPAD_PID      = 0x0009

    def __init__(self):
        super().__init__()
        self.title("BaseCamp Linux")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.geometry("480x760")

        # Enable drag & drop globally — soft-fails if tkinterdnd2 is missing.
        self._dnd_available = False
        try:
            from tkinterdnd2 import TkinterDnD
            TkinterDnD._require(self)
            self._dnd_available = True
        except Exception:
            pass

        try:
            _icon = ImageTk.PhotoImage(Image.open(
                os.path.join(_RES, "resources", "app_icon_64.png")))
            self.iconphoto(True, _icon)
        except Exception:
            pass

        # i18n
        self._lang          = {}
        self._i18n_widgets  = []
        self._avail_langs   = available_langs()

        def _read_cfg(name, default):
            try:
                with open(os.path.join(CONFIG_DIR, name)) as f:
                    return f.read().strip()
            except FileNotFoundError:
                return default

        code = _read_cfg("language", "de")
        if code not in self._avail_langs:
            code = "de"
        self._lang      = load_lang(code)
        self._lang_code = code
        self._rebuild_obs_type_map()

        self._lang_var = tk.StringVar()

        self._active_device = None   # "everest_max" | "everest60" | "makalu67" | "displaypad"
        self._panels        = {}     # populated in _build_ui
        self._kb_panel_id   = "everest_max"   # which keyboard panel is active
        self._dev_present   = {"everest_max": False, "everest60": False,
                               "makalu67": False, "displaypad": False, "obs": False}

        # Plugin system
        self._plugin_manager = PluginManager()
        self._plugin_manager.discover()
        self._plugin_ctx = PluginContext(self, self._plugin_manager)
        self._plugin_manager.load_all(self._plugin_ctx)

        self._build_ui()

        # Populate language combo (now that EverestMaxPanel has created it)
        lang_names   = list(self._avail_langs.values())
        current_name = self._avail_langs.get(self._lang_code, "")
        self._lang_var.set(current_name)
        if hasattr(self, "_everest_panel"):
            self._everest_panel._lang_combo.configure(values=lang_names)

        self._restore_debounce_id = None
        self._was_withdrawn = False
        self._setup_tray()
        self.protocol("WM_DELETE_WINDOW", self._hide_window)
        self.bind("<Unmap>", lambda e: self._hide_window() if self.state() == "iconic" else None)
        # Recover from display sleep — force refresh only after withdraw/deiconify
        self.bind("<Map>", self._on_window_restore)
        self.after(500, self._start_cpu_auto_clean)
        # Run first device check immediately so the correct panel is shown
        self._check_devices()
        # Background update check — non-blocking, only sets a label if newer found
        self._update_message = ""
        self._update_url = ""
        self._update_sha_url = ""
        self._update_version = ""
        self._update_install_type = ""
        # _update_kind = "source" prefers the small overlay tarball (~200 KB
        # for typical patches); "appimage" downloads the full ~250 MB image.
        # Source updates are only chosen when a source-*.tar.gz asset exists
        # on the release, otherwise we fall back to AppImage.
        self._update_kind = ""
        self.after(2000, self._check_for_update)
        # Plugin update count is filled in by PluginManagerPanel after its
        # background fetch (which runs unconditionally on app start) — it
        # calls back into _on_plugins_fetched to decorate the sidebar button.
        self._plugin_update_count = 0

    # ── subprocess command builder ────────────────────────────────────────────

    def _cmd(self, *args):
        """Build subprocess command for Everest Max controller (default device)."""
        return _cmd(*args)

    def _cmd_for_device(self, device_id, *args):
        """Build subprocess command for a specific device controller."""
        if device_id == "makalu67":
            script = os.path.join(_HERE, "devices", "makalu67", "controller.py")
            if _FROZEN:
                return [os.path.join(_BIN, "makalu-controller")] + list(args)
            return [PYTHON, script] + list(args)
        if device_id == "everest60":
            script = os.path.join(_HERE, "devices", "everest60", "controller.py")
            if _FROZEN:
                return [os.path.join(_BIN, "everest60-controller")] + list(args)
            return [PYTHON, script] + list(args)
        return _cmd(*args)

    # ── i18n ──────────────────────────────────────────────────────────────────

    def T(self, key, **kwargs):
        val = self._lang.get(key, key)
        if kwargs:
            try:
                val = val.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return val

    def _reg(self, widget, key, attr="text"):
        self._i18n_widgets.append((widget, key, attr))
        return widget

    def _rebuild_obs_type_map(self):
        self._obs_type_options = {
            internal: self._lang.get(f"obs_{internal}", internal)
            for internal in OBS_INTERNAL_ORDER
        }
        self._obs_type_display_to_internal = {
            v: k for k, v in self._obs_type_options.items()
        }

    def _load_lang_code(self, code):
        self._lang      = load_lang(code)
        self._lang_code = code
        self._rebuild_obs_type_map()
        self._apply_lang()

    def _apply_lang(self):
        for widget, key, attr in self._i18n_widgets:
            try:
                widget.configure(**{attr: self.T(key)})
            except Exception:
                pass
        # Delegate to active panel for panel-specific i18n (OBS combos, type menus)
        for panel in self._panels.values():
            if hasattr(panel, "apply_lang"):
                panel.apply_lang()

    def _on_lang_change(self, val=None):
        selected_name = val if val is not None else self._lang_var.get()
        code = None
        for c, name in self._avail_langs.items():
            if name == selected_name:
                code = c
                break
        if code is None:
            return
        with open(os.path.join(CONFIG_DIR, "language"), "w") as f:
            f.write(code)
        self._load_lang_code(code)

    def _pick_gif_frame(self, path, n_frames):
        dlg = ctk.CTkToplevel(self)
        dlg.title(self.T("gif_frame_title", n=n_frames))
        dlg.configure(fg_color=BG)
        dlg.resizable(False, False)
        dlg.grab_set()

        result    = [0]
        cancelled = [False]

        preview_label = ctk.CTkLabel(dlg, text="", width=144, height=144,
                                      fg_color=BG3)
        preview_label.pack(pady=(12, 2), padx=16)

        info_label = ctk.CTkLabel(dlg, text="", fg_color="transparent",
                                   text_color=FG2, font=("Helvetica", 11))
        info_label.pack()

        gif_img = Image.open(path)
        _photo  = [None]

        def _update_preview(frame_val):
            try:
                frame_idx = int(float(frame_val))
                gif_img.seek(frame_idx)
                frame    = gif_img.copy().resize((144, 144), Image.LANCZOS).convert("RGB")
                ctk_img  = ctk.CTkImage(light_image=frame, dark_image=frame,
                                         size=(144, 144))
                _photo[0] = ctk_img
                preview_label.configure(image=ctk_img)
                info_label.configure(text=self.T("gif_frame_info",
                                                  frame=frame_idx + 1, total=n_frames))
            except Exception:
                pass

        slider = ctk.CTkSlider(dlg, from_=0, to=n_frames - 1,
                                number_of_steps=n_frames - 1,
                                command=_update_preview,
                                width=200, progress_color=BLUE, button_color=FG,
                                fg_color=BG3)
        slider.set(0)
        slider.pack(pady=(6, 2), padx=16)
        _update_preview(0)

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(pady=(6, 12))

        def _ok():
            result[0] = int(slider.get())
            dlg.destroy()

        def _cancel():
            cancelled[0] = True
            dlg.destroy()

        ctk.CTkButton(btn_row, text="OK", command=_ok,
                      fg_color=BLUE, text_color=FG, hover_color="#0884be",
                      font=("Helvetica", 11, "bold"), height=30, width=70,
                      corner_radius=6).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text=self.T("gif_frame_cancel"), command=_cancel,
                      fg_color=BG3, text_color=FG, hover_color=BG2,
                      font=("Helvetica", 11), height=30, width=70,
                      corner_radius=6).pack(side="left")

        dlg.wait_window()
        return None if cancelled[0] else result[0]

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header bar ──
        hdr = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(inner, text="MOUNTAIN", font=("Helvetica", 15, "bold"),
                     text_color=FG).pack(side="left")
        ctk.CTkLabel(inner, text=" BASECAMP", font=("Helvetica", 15, "bold"),
                     text_color=BLUE).pack(side="left")
        ctk.CTkButton(hdr, text="✕", width=32, height=32, corner_radius=6,
                      fg_color="transparent", hover_color=BG3, text_color=FG2,
                      font=("Helvetica", 14), command=self._quit).place(relx=1.0,
                      rely=0.5, anchor="e", x=-8)
        self._settings_btn = ctk.CTkButton(
            hdr, text="⚙", width=32, height=32, corner_radius=6,
            fg_color="transparent", hover_color=BG3, text_color=FG2,
            font=("Helvetica", 16), command=self._open_settings)
        self._settings_btn.place(relx=1.0, rely=0.5, anchor="e", x=-44)

        # ── Device switcher bar (2 rows) ──
        switcher = ctk.CTkFrame(self, fg_color=BG3, corner_radius=0)
        switcher.pack(fill="x")

        row1 = ctk.CTkFrame(switcher, fg_color="transparent")
        row1.pack(pady=(4, 0))

        self._sw_keyboard_btn = ctk.CTkButton(
            row1, text="Keyboard", font=("Helvetica", 11, "bold"),
            fg_color=BLUE, hover_color="#0884be", text_color=FG,
            height=28, corner_radius=4,
            command=lambda: self._switch_device(self._kb_panel_id))
        self._sw_keyboard_btn.pack(side="left", padx=4)

        self._sw_mouse_btn = ctk.CTkButton(
            row1, text="Mouse", font=("Helvetica", 11, "bold"),
            fg_color=BG2, hover_color="#222232", text_color=FG2,
            height=28, corner_radius=4,
            command=lambda: self._switch_device("makalu67"))
        self._sw_mouse_btn.pack(side="left", padx=4)

        self._sw_displaypad_btn = ctk.CTkButton(
            row1, text="DisplayPad", font=("Helvetica", 11, "bold"),
            fg_color=BG2, hover_color="#222232", text_color=FG2,
            height=28, corner_radius=4,
            command=lambda: self._switch_device("displaypad"))
        self._sw_displaypad_btn.pack(side="left", padx=4)

        row2 = ctk.CTkFrame(switcher, fg_color="transparent")
        row2.pack(pady=(2, 4))

        self._sw_obs_btn = ctk.CTkButton(
            row2, text="OBS Studio", font=("Helvetica", 11, "bold"),
            fg_color=BG2, hover_color="#222232", text_color=FG2,
            height=28, corner_radius=4, width=110,
            command=lambda: self._switch_device("obs"))
        self._sw_obs_btn.pack(side="left", padx=4)

        self._sw_macros_btn = ctk.CTkButton(
            row2, text="Macros", font=("Helvetica", 11, "bold"),
            fg_color=BG2, hover_color="#222232", text_color=FG2,
            height=28, corner_radius=4, width=90,
            command=lambda: self._switch_device("macros"))
        self._sw_macros_btn.pack(side="left", padx=4)

        self._sw_plugins_btn = ctk.CTkButton(
            row2, text="Plugins", font=("Helvetica", 11, "bold"),
            fg_color=BG2, hover_color="#222232", text_color=FG2,
            height=28, corner_radius=4, width=90,
            command=lambda: self._switch_device("plugins"))
        self._sw_plugins_btn.pack(side="left", padx=4)

        # ── Panel area ──
        self._panel_area = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._panel_area.pack(fill="both", expand=True)

        # Instantiate panels (OBS first — other panels reference it)
        self._obs_panel         = OBSPanel(self._panel_area, self)
        self._macro_panel       = MacroPanel(self._panel_area, self)
        self._everest_panel     = EverestMaxPanel(self._panel_area, self)
        self._everest60_panel   = Everest60Panel(self._panel_area, self)
        self._makalu_panel      = Makalu67Panel(self._panel_area, self)
        self._displaypad_panel  = DisplayPadPanel(self._panel_area, self)
        self._plugins_panel     = PluginManagerPanel(self._panel_area, self)

        self._panels = {
            "everest_max": self._everest_panel,
            "everest60":   self._everest60_panel,
            "makalu67":    self._makalu_panel,
            "displaypad":  self._displaypad_panel,
            "obs":         self._obs_panel,
            "macros":      self._macro_panel,
            "plugins":     self._plugins_panel,
        }

        # ── Plugin panels ──
        self._plugin_sw_btns = {}
        plugin_panels = list(self._plugin_manager.get_panel_plugins())
        if plugin_panels:
            row3 = ctk.CTkFrame(switcher, fg_color="transparent")
            row3.pack(pady=(2, 4))
            for pid, info, inst in plugin_panels:
                try:
                    panel = inst.create_panel(self._panel_area)
                    self._panels[pid] = panel
                    label = getattr(inst, "panel_label", info.get("name", pid))
                    btn = ctk.CTkButton(
                        row3, text=label, font=("Helvetica", 11, "bold"),
                        fg_color=BG2, hover_color="#222232", text_color=FG2,
                        height=28, corner_radius=4, width=110,
                        command=lambda p=pid: self._switch_device(p))
                    btn.pack(side="left", padx=4)
                    self._plugin_sw_btns[pid] = btn
                except Exception as e:
                    print(f"[Plugin] Failed to create panel for {pid}: {e}")

        # Start plugin services after UI is ready
        self.after(100, self._plugin_manager.start_services)

        # Show keyboard panel by default
        self._switch_device("everest_max")

    # ── Device switching ──────────────────────────────────────────────────────

    def _switch_device(self, device_id):
        if self._active_device == device_id:
            return
        # Hide all panels
        for panel in self._panels.values():
            panel.pack_forget()
        # Show selected panel
        self._panels[device_id].pack(fill="both", expand=True)
        self._active_device = device_id

        # Update switcher button styles
        self._refresh_switcher_colors()

        # Force CTkButtons/widgets to redraw — CTk skips internal canvas
        # draw for widgets that were built while their panel was hidden
        self.after(20, self._redraw_panel_widgets, device_id)

    def _redraw_panel_widgets(self, device_id):
        """Walk the active panel and force _draw() on all CTk widgets."""
        panel = self._panels.get(device_id)
        if not panel or not panel.winfo_exists():
            return
        self._force_draw_children(panel)

    def _force_draw_children(self, widget):
        """Recursively call _draw() on CTk widgets that have it."""
        if hasattr(widget, "_draw") and callable(widget._draw):
            try:
                widget._draw()
            except Exception:
                pass
        for child in widget.winfo_children():
            self._force_draw_children(child)

    # ── Controller delegation ─────────────────────────────────────────────────

    def _stop_cpu_proc(self):
        """Stop CPU monitor on active panel. Returns True if was running."""
        panel = self._panels.get(self._active_device)
        if panel and hasattr(panel, "_stop_cpu_proc"):
            return panel._stop_cpu_proc()
        return False

    def _start_cpu_auto(self):
        """Start CPU monitor on active panel."""
        panel = self._panels.get(self._active_device)
        if panel and hasattr(panel, "_start_cpu_auto"):
            panel._start_cpu_auto()

    def _start_cpu_auto_clean(self):
        """Delegate to Everest panel (only keyboard has CPU monitor)."""
        if hasattr(self, "_everest_panel"):
            self._everest_panel._start_cpu_auto_clean()

    # ── USB presence check ────────────────────────────────────────────────────

    def _check_devices(self):
        """Periodic USB presence check (runs in main thread — /sys reads are <1ms)."""
        kb_max_present = _check_usb_presence(self.EVEREST_MAX_VID, self.EVEREST_MAX_PID)
        kb_60_present  = (_check_usb_presence(self.EVEREST60_VID, self.EVEREST60_PID_ANSI)
                          or _check_usb_presence(self.EVEREST60_VID, self.EVEREST60_PID_ISO))
        mouse_present  = (_check_usb_presence(self.MAKALU67_VID, self.MAKALU67_PID)
                          or _check_usb_presence(self.MAKALU67_VID, 0x0002))
        dp_present     = _check_usb_presence(self.DISPLAYPAD_VID, self.DISPLAYPAD_PID)
        self._update_device_status(kb_max_present, kb_60_present, mouse_present, dp_present)
        self.after(5000, self._check_devices)

    def _update_device_status(self, kb_max_present, kb_60_present=False,
                               mouse_present=False, dp_present=False):
        """Update switcher button appearance based on device presence."""
        obs_connected = hasattr(self, "_obs_panel") and self._obs_panel.is_connected()
        self._dev_present["everest_max"] = kb_max_present
        self._dev_present["everest60"]   = kb_60_present
        self._dev_present["makalu67"]    = mouse_present
        self._dev_present["displaypad"]  = dp_present
        self._dev_present["obs"]         = obs_connected
        # Determine active keyboard panel (Everest 60 takes priority if connected)
        old_kb_id = self._kb_panel_id
        if kb_60_present:
            self._kb_panel_id = "everest60"
        elif kb_max_present:
            self._kb_panel_id = "everest_max"
        # Auto-switch if viewing a keyboard panel that changed
        if (self._active_device in ("everest_max", "everest60")
                and self._kb_panel_id != old_kb_id):
            self._active_device = None  # force re-switch
            self._switch_device(self._kb_panel_id)
        # Update button labels
        mouse_label = getattr(self._makalu_panel, "_model_name", "Mouse") if hasattr(self, "_makalu_panel") else "Mouse"
        if kb_60_present and hasattr(self, "_everest60_panel"):
            kb_label = getattr(self._everest60_panel, "_model_name", "Everest 60")
        elif kb_max_present:
            kb_label = "Everest Max"
        else:
            kb_label = "Keyboard"
        self._sw_keyboard_btn.configure(text=kb_label)
        self._sw_mouse_btn.configure(text=mouse_label)
        self._sw_displaypad_btn.configure(text="DisplayPad")
        self._refresh_switcher_colors()
        # Notify panels
        if hasattr(self, "_makalu_panel"):
            self._makalu_panel.set_connected(mouse_present)
        if hasattr(self, "_everest60_panel"):
            self._everest60_panel.set_connected(kb_60_present)

    def _refresh_switcher_colors(self):
        """Apply fg_color/text_color to each switcher button: blue=active, green=present, gray=absent."""
        # Keyboard button covers both Everest Max and Everest 60
        kb_active  = self._active_device in ("everest_max", "everest60")
        kb_present = (self._dev_present.get("everest_max", False)
                      or self._dev_present.get("everest60", False))
        if kb_active:
            self._sw_keyboard_btn.configure(fg_color=BLUE, text_color=FG)
        elif kb_present:
            self._sw_keyboard_btn.configure(fg_color=GRN, text_color=FG)
        else:
            self._sw_keyboard_btn.configure(fg_color=BG2, text_color=FG2)

        btn_list = [
            ("makalu67",   self._sw_mouse_btn),
            ("displaypad", self._sw_displaypad_btn),
            ("obs",        self._sw_obs_btn),
            ("macros",     self._sw_macros_btn),
            ("plugins",    self._sw_plugins_btn),
        ]
        # Include plugin switcher buttons
        for pid, btn in getattr(self, "_plugin_sw_btns", {}).items():
            btn_list.append((pid, btn))

        for dev_id, btn in btn_list:
            active  = self._active_device == dev_id
            present = self._dev_present.get(dev_id, False)
            if active:
                btn.configure(fg_color=BLUE, text_color=FG)
            elif present:
                btn.configure(fg_color=GRN, text_color=FG)
            else:
                btn.configure(fg_color=BG2, text_color=FG2)

    # ── Tray / lifecycle ──────────────────────────────────────────────────────

    def _setup_tray(self):
        import signal as _signal
        _signal.signal(_signal.SIGUSR1, lambda *_: self.after(0, self._show_window))
        _signal.signal(_signal.SIGUSR2, lambda *_: self.after(0, self._quit))

        lang_file = os.path.join(LANG_DIR, f"{self._lang_code}.json")
        env = os.environ.copy()
        if os.environ.get("SUDO_USER"):
            user = os.environ["SUDO_USER"]
            uid  = _pwd.getpwnam(user).pw_uid
            env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
            env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
            if _FROZEN:
                cmd = ["sudo", "-u", user, "-E", TRAY_HELPER,
                       str(os.getpid()), lang_file]
            else:
                cmd = ["sudo", "-u", user, "-E", sys.executable, TRAY_HELPER,
                       str(os.getpid()), lang_file]
        else:
            if _FROZEN:
                cmd = [TRAY_HELPER, str(os.getpid()), lang_file]
            else:
                cmd = [sys.executable, TRAY_HELPER, str(os.getpid()), lang_file]
        self._tray_proc = subprocess.Popen(cmd, env=env)

    def _on_window_restore(self, event=None):
        """Force UI refresh after withdraw/deiconify (tray restore or display sleep)."""
        if not self._was_withdrawn:
            return
        self._was_withdrawn = False
        if self._restore_debounce_id is not None:
            self.after_cancel(self._restore_debounce_id)
        self._restore_debounce_id = self.after(200, self._do_window_restore)

    def _do_window_restore(self):
        """Actual restore logic, called once after debounce settles."""
        self._restore_debounce_id = None
        try:
            geo = self.geometry()
            self.geometry(geo)
            self.update_idletasks()
            self._refresh_switcher_colors()
            if self._active_device and self._active_device in self._panels:
                panel = self._panels[self._active_device]
                panel.pack_forget()
                panel.pack(fill="both", expand=True)
            self.lift()
        except Exception:
            pass

    def _hide_window(self):
        self._was_withdrawn = True
        self.withdraw()

    def _show_window(self):
        self.deiconify()
        self.lift()

    def _detect_install_type(self):
        """Return one of 'appimage' | 'arch' | 'debian' | 'source'.
        Picked at runtime so the same code works across all packaging formats."""
        if os.environ.get("APPIMAGE"):
            return "appimage"
        # AUR builds install a binary at /usr/bin/basecamp-linux — but Arch users
        # could also be running from source. Check pacman db for our package.
        if os.path.exists("/etc/arch-release"):
            try:
                r = subprocess.run(["pacman", "-Q", "basecamp-linux"],
                                    capture_output=True, timeout=2)
                if r.returncode == 0:
                    return "arch"
            except Exception:
                pass
        if os.path.exists("/etc/debian_version"):
            try:
                r = subprocess.run(["dpkg", "-s", "basecamp-linux"],
                                    capture_output=True, timeout=2)
                if r.returncode == 0:
                    return "debian"
            except Exception:
                pass
        return "source"

    def _check_for_update(self):
        """Async fetch latest release tag from GitHub and compare with APP_VERSION.
        Fail-quiet on any network/parse error."""
        import threading

        def _version_tuple(s):
            parts = []
            for p in s.lstrip("v").split("."):
                num = "".join(c for c in p if c.isdigit())
                parts.append(int(num) if num else 0)
            return tuple(parts)

        def _run():
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.github.com/repos/ramisotti13-eng/BaseCamp-Linux/releases/latest",
                    headers={"User-Agent": f"BaseCamp-Linux/{APP_VERSION}"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                tag = (data.get("tag_name") or "").strip()
                if tag and _version_tuple(tag) > _version_tuple(APP_VERSION):
                    ver = tag.lstrip("v")
                    install_type = self._detect_install_type()
                    # Per-distro instruction — the install_type drives which
                    # follow-up command the user needs to run.
                    hint = self.T(f"settings_update_hint_{install_type}")
                    msg = (self.T("settings_update_available", ver=ver)
                            + "\n" + hint)
                    # Prefer source-overlay tarball when the release ships one
                    # — it's ~1500× smaller than the AppImage and works across
                    # both Debian and Fedora builds. Only when native deps
                    # changed (no source tarball published) do we fall back to
                    # the full AppImage download.
                    # A matching .sha256 sidecar is REQUIRED; without it we
                    # silently fall back to the AppImage path, because an
                    # unsigned tarball is the easiest tamper point on the
                    # update flow (compromised release → arbitrary code).
                    source_url = ""
                    source_sha_url = ""
                    if install_type == "appimage":
                        for asset in data.get("assets") or []:
                            name = (asset.get("name") or "").lower()
                            if name.startswith("source-") and name.endswith(".tar.gz"):
                                source_url = asset.get("browser_download_url") or ""
                            elif name.startswith("source-") and name.endswith(".tar.gz.sha256"):
                                source_sha_url = asset.get("browser_download_url") or ""
                        if not source_sha_url:
                            source_url = ""
                    # AppImage installs: pick the asset that matches the
                    # distro family. Filename of the running AppImage wins if
                    # it explicitly says -debian/-fedora (user picked it on
                    # download); otherwise read /etc/os-release to decide.
                    # Debian-family glibc is older than Fedora's, so the wrong
                    # variant will fail to start with cryptic ld errors.
                    url = ""
                    if install_type == "appimage":
                        appimg = os.environ.get("APPIMAGE", "") or ""
                        base = os.path.basename(appimg).lower()
                        if "debian" in base:
                            variant = "debian"
                        elif "fedora" in base:
                            variant = "fedora"
                        else:
                            variant = "fedora"
                            try:
                                with open("/etc/os-release") as f:
                                    osr = f.read().lower()
                                if ("id=debian" in osr or "id=ubuntu" in osr
                                        or "id=linuxmint" in osr
                                        or "id_like=debian" in osr
                                        or "id_like=ubuntu" in osr):
                                    variant = "debian"
                            except OSError:
                                pass
                        for asset in data.get("assets") or []:
                            name = (asset.get("name") or "").lower()
                            if name.endswith(".appimage") and variant in name:
                                url = asset.get("browser_download_url") or ""
                                break
                        if not url:
                            for asset in data.get("assets") or []:
                                name = (asset.get("name") or "").lower()
                                if name.endswith(".appimage"):
                                    url = asset.get("browser_download_url") or ""
                                    break
                    def _apply():
                        self._update_message = msg
                        # Pick the actionable URL: source if available, else
                        # the full AppImage. The popup/button trigger logic
                        # only checks _update_url, so this stays transparent.
                        self._update_url = source_url or url
                        self._update_sha_url = source_sha_url
                        self._update_kind = "source" if source_url else "appimage"
                        self._update_version = ver
                        self._update_install_type = install_type
                        # Decorate the settings cog so the update is visible
                        # without opening the dialog. Works for any install
                        # type — source/AUR users still see "open me" too.
                        if hasattr(self, "_settings_btn"):
                            self._settings_btn.configure(
                                text="⚙ ↑", text_color=GRN)
                        # Proactive popup — only for AppImage installs where
                        # we can actually do something about it from the GUI.
                        if install_type == "appimage" and url:
                            self._show_update_popup()
                    self.after(0, _apply)
            except Exception:
                pass  # offline / rate-limited / dns — silent

        threading.Thread(target=_run, daemon=True).start()

    def _show_update_popup(self):
        """Open the proactive update popup. Guarded against double-spawn so
        repeated _check_for_update calls don't stack windows."""
        existing = getattr(self, "_update_popup", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.focus()
                    return
            except Exception:
                pass
        self._update_popup = UpdateAvailableDialog(self)

    def run_update_download(self, on_progress, on_installing, on_done, on_error):
        """Threaded download + install of an update. Dispatches on
        self._update_kind:
          - "source": download source-X.Y.Z.tar.gz, verify SHA256 against the
            .sha256 sidecar from the release (mandatory), extract to
            ~/.local/share/basecamp-linux/source-overlay/. AppImage binary
            stays untouched. Tiny (~200 KB), works on both Debian + Fedora.
          - "appimage": full AppImage swap via atomic rename (~250 MB).
        UI-agnostic — callbacks fire on the Tk thread."""
        import threading, urllib.request, hashlib
        url     = getattr(self, "_update_url", "")
        sha_url = getattr(self, "_update_sha_url", "")
        kind    = getattr(self, "_update_kind", "appimage")
        appimg  = os.environ.get("APPIMAGE", "")
        if not url or not appimg or not os.path.isfile(appimg):
            on_error(self.T("settings_update_no_asset"))
            return
        if kind == "source" and not sha_url:
            # Belt-and-suspenders — _check_for_update already drops source_url
            # in this case, but guard here too.
            on_error(self.T("settings_update_no_checksum"))
            return

        def _install_source(tarball_path):
            """Extract source tarball to overlay dir. Stages into a sibling
            directory then renames so a half-extracted tree never replaces
            the running one (which the bootstrap hook would happily load)."""
            import tarfile, shutil
            overlay_root = os.path.join(_real_home, ".local", "share",
                                        "basecamp-linux")
            os.makedirs(overlay_root, exist_ok=True)
            staging  = os.path.join(overlay_root, "source-overlay.new")
            final    = os.path.join(overlay_root, "source-overlay")
            if os.path.exists(staging):
                shutil.rmtree(staging)
            os.makedirs(staging)
            with tarfile.open(tarball_path, "r:gz") as tf:
                # Strip the top-level 'source-overlay/' dir so members land
                # directly in our staging path.
                def _members():
                    for m in tf.getmembers():
                        parts = m.name.split("/", 1)
                        if len(parts) < 2 or parts[0] != "source-overlay":
                            continue
                        m.name = parts[1]
                        if not m.name:
                            continue
                        yield m
                # filter="data" (Python 3.12+) rejects path traversal, absolute
                # paths, symlinks pointing outside dest, device nodes, and
                # strips setuid/setgid bits. Fall back to manual checks on
                # older Python; the source tarball is produced by us so the
                # added value of data_filter is defense-in-depth against a
                # compromised release pipeline.
                try:
                    tf.extractall(staging, members=_members(), filter="data")
                except TypeError:
                    for m in _members():
                        if (m.name.startswith("/")
                                or ".." in m.name.split("/")
                                or m.issym() or m.islnk()
                                or m.isdev() or m.ischr() or m.isfifo()):
                            continue
                        tf.extract(m, staging)
            if not os.path.isfile(os.path.join(staging, "gui.py")):
                raise RuntimeError("source tarball missing gui.py")
            if os.path.exists(final):
                shutil.rmtree(final)
            os.replace(staging, final)

        def _fetch_text(u, max_bytes=256):
            """Fetch a tiny file (sha256 sidecar). Bounded to avoid surprises
            if the URL serves something unexpectedly large."""
            req = urllib.request.Request(
                u, headers={"User-Agent": f"BaseCamp-Linux/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read(max_bytes).decode("utf-8", "replace")

        def _run():
            tmp_path = (appimg + ".new") if kind == "appimage" \
                       else os.path.join(_real_home, ".cache",
                                         "basecamp-source-update.tar.gz")
            try:
                expected_sha = ""
                if kind == "source":
                    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
                    # Fetch checksum sidecar FIRST. If this fails we abort
                    # before even touching the tarball.
                    raw = _fetch_text(sha_url).strip().split()
                    if raw:
                        expected_sha = raw[0].lower()
                    if len(expected_sha) != 64 or not all(
                            c in "0123456789abcdef" for c in expected_sha):
                        self.after(0, on_error,
                                   self.T("settings_update_bad_checksum"))
                        return
                req = urllib.request.Request(
                    url, headers={"User-Agent": f"BaseCamp-Linux/{APP_VERSION}"})
                hasher = hashlib.sha256()
                with urllib.request.urlopen(req, timeout=15) as resp:
                    total = int(resp.headers.get("Content-Length") or 0)
                    done, last = 0, -1
                    with open(tmp_path, "wb") as out:
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            out.write(chunk)
                            hasher.update(chunk)
                            done += len(chunk)
                            if total > 0:
                                pct = int(done * 100 / total)
                                if pct != last:
                                    last = pct
                                    self.after(0, on_progress, pct)
                if kind == "source":
                    actual_sha = hasher.hexdigest().lower()
                    if actual_sha != expected_sha:
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                        self.after(0, on_error,
                                   self.T("settings_update_bad_checksum"))
                        return
                self.after(0, on_installing)
                if kind == "source":
                    _install_source(tmp_path)
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                else:
                    os.chmod(tmp_path, 0o755)
                    os.replace(tmp_path, appimg)
                self.after(0, on_done)
            except Exception as e:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                self.after(0, on_error, str(e)[:80])

        threading.Thread(target=_run, daemon=True).start()

    def restart_after_update(self):
        """Re-exec the (now updated) AppImage. Kills the tray helper first —
        execv preserves the PID, so the helper would otherwise sit on the new
        process and a second tray would spawn on next startup."""
        tray = getattr(self, "_tray_proc", None)
        if tray is not None and tray.poll() is None:
            try:
                tray.terminate()
                tray.wait(timeout=2)
            except Exception:
                try:
                    tray.kill()
                except Exception:
                    pass
        appimg = os.environ.get("APPIMAGE", "")
        try:
            if appimg and os.path.isfile(appimg):
                os.execv(appimg, [appimg])
        except Exception:
            pass
        try:
            subprocess.Popen([appimg] if appimg else [sys.executable])
        except Exception:
            pass
        self.destroy()

    def _on_plugins_fetched(self, plugins):
        """Called by PluginManagerPanel after a successful plugins.json fetch.
        Counts published versions newer than installed and decorates the
        Plugins switcher button so users see updates without opening the panel."""
        def _version_tuple(s):
            parts = []
            for p in str(s or "").lstrip("v").split("."):
                num = "".join(c for c in p if c.isdigit())
                parts.append(int(num) if num else 0)
            return tuple(parts) or (0,)

        count = 0
        pm = self._plugin_manager
        for pinfo in plugins or []:
            pid = pinfo.get("id")
            if not pid or pid not in pm._manifests:
                continue
            if _version_tuple(pinfo.get("version", "0")) > \
               _version_tuple(pm._manifests[pid].get("version", "0")):
                count += 1
        self._plugin_update_count = count
        if hasattr(self, "_sw_plugins_btn"):
            if count > 0:
                self._sw_plugins_btn.configure(
                    text=f"Plugins  ↑{count}", text_color=GRN)
            else:
                self._sw_plugins_btn.configure(text="Plugins")

    def _open_settings(self):
        if getattr(self, "_settings_win", None) is not None:
            try:
                if self._settings_win.winfo_exists():
                    self._settings_win.focus()
                    return
            except Exception:
                pass
        self._settings_win = SettingsDialog(self)

    def _quit(self):
        self.destroy()

    def destroy(self):
        # Signal all background HID threads to stop
        if hasattr(self, "_displaypad_panel"):
            p = self._displaypad_panel
            if hasattr(p, "_monitor_stop"):
                p._monitor_stop.set()
            if hasattr(p, "_key_stop"):
                p._key_stop.set()
            if hasattr(p, "_anim_stop"):
                p._anim_stop.set()
        # Stop Everest panel CPU proc if running
        if hasattr(self, "_everest_panel"):
            if self._everest_panel._cpu_proc and \
               self._everest_panel._cpu_proc.poll() is None:
                self._everest_panel._cpu_proc.terminate()
        if hasattr(self, "_tray_proc") and self._tray_proc.poll() is None:
            self._tray_proc.terminate()
        # Shutdown plugins
        if hasattr(self, "_plugin_manager"):
            self._plugin_manager.shutdown()
        # Give HID threads time to close their devices before tearing down
        import time
        time.sleep(0.4)
        super().destroy()


# ── Splash screen ─────────────────────────────────────────────────────────────

def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    img   = Image.open(os.path.join(_RES, "resources", "logo.png")).convert("RGBA")
    img   = img.resize((768, 512), Image.LANCZOS)
    bg    = Image.new("RGBA", img.size, BG)
    bg.paste(img, mask=img.split()[3])
    photo = ImageTk.PhotoImage(bg.convert("RGB"))
    w, h  = img.size
    sw    = splash.winfo_screenwidth()
    sh    = splash.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    splash.configure(bg=BG)
    tk.Label(splash, image=photo, bd=0, bg=BG).pack()
    splash.after(3500, splash.destroy)
    splash.mainloop()


def _install_desktop_entry():
    """Install .desktop file and icon to ~/.local/share/ for app menu integration."""
    import shutil
    app_dir       = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    appimage_path = os.environ.get("APPIMAGE", os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))

    icon_src = os.path.join(app_dir, "_internal", "resources", "app_icon_256.png")
    if not os.path.exists(icon_src):
        icon_src = os.path.join(app_dir, "resources", "app_icon_256.png")
    icon_dst = os.path.join(_real_home, ".local", "share", "icons", "hicolor",
                             "256x256", "apps", "basecamp-linux.png")
    os.makedirs(os.path.dirname(icon_dst), exist_ok=True)
    shutil.copy2(icon_src, icon_dst)

    desktop_dir  = os.path.join(_real_home, ".local", "share", "applications")
    os.makedirs(desktop_dir, exist_ok=True)
    desktop_path = os.path.join(desktop_dir, "basecamp-linux.desktop")
    with open(desktop_path, "w") as f:
        f.write(f"""[Desktop Entry]
Name=BaseCamp Linux
Comment=Unofficial Linux companion app for the Mountain Everest Max keyboard
Exec="{appimage_path}"
Icon=basecamp-linux
Type=Application
Categories=Utility;
""")
    os.chmod(desktop_path, 0o755)
    print(f"Installed: {desktop_path}")
    print(f"Installed: {icon_dst}")

    # Update autostart .desktop if it exists
    if os.path.exists(AUTOSTART_FILE):
        with open(AUTOSTART_FILE, "w") as f:
            f.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=BaseCamp Linux\n"
                "Comment=Mountain Everest Max display control\n"
                f'Exec="{appimage_path}" --minimized\n'
                "Icon=basecamp-linux\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
        print(f"Updated:   {AUTOSTART_FILE}")

    # Refresh desktop cache so the launcher picks up the new .desktop immediately
    try:
        subprocess.run(["update-desktop-database", desktop_dir],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

    print("Done. BaseCamp Linux should now appear in your app menu.")


def run():
    """Real entry point — kept as a function so the AppImage's tiny
    appentry.py shim can call it after wiring up the source-overlay path.
    Running `python gui.py` directly still works because of __main__ below."""
    if "--install" in sys.argv:
        _install_desktop_entry()
        sys.exit(0)
    psutil.cpu_percent()
    start_minimized = "--minimized" in sys.argv
    if not start_minimized and load_splash_enabled():
        show_splash()
    app = App()
    if start_minimized:
        app._was_withdrawn = True
        app.withdraw()
    app.mainloop()


if __name__ == "__main__":
    run()
