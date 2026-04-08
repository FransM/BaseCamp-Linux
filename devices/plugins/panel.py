"""Plugin Manager panel -- view, enable, disable, install plugins."""
import json
import os
import shutil
import threading
import urllib.request
import zipfile
import tempfile
import customtkinter as ctk
from PIL import Image

from shared.ui_helpers import BG, BG2, BG3, FG, FG2, BLUE, GRN, RED, YLW, BORDER
from shared.config import CONFIG_DIR

_PLUGINS_DIR = os.path.join(CONFIG_DIR, "plugins")

# Type badge colors
_TYPE_COLORS = {
    "panel":   ("#0ea5e9", "#0c4a6e"),   # blue fg, blue bg
    "service": ("#22c55e", "#14532d"),    # green fg, green bg
    "action":  ("#f59e0b", "#78350f"),    # amber fg, amber bg
}


class PluginManagerPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self._app = app
        self._rows = {}  # pid -> dict of widgets
        self._expanded = set()  # pids that are expanded
        self._icon_cache = {}  # pid -> CTkImage
        self._build_ui()

    def T(self, key, **kw):
        return self._app.T(key, **kw)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 4))

        self._title_lbl = ctk.CTkLabel(
            hdr, text=self.T("pluginmgr_title"),
            font=("Helvetica", 14, "bold"), text_color=FG)
        self._title_lbl.pack(side="left")

        self._count_lbl = ctk.CTkLabel(
            hdr, text="", font=("Helvetica", 11), text_color=FG2)
        self._count_lbl.pack(side="right")

        # Hint
        self._hint_lbl = ctk.CTkLabel(
            self, text=self.T("pluginmgr_hint"),
            font=("Helvetica", 10), text_color=FG2, justify="left")
        self._hint_lbl.pack(fill="x", padx=16, pady=(0, 8))

        # Plugin list
        self._list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="x", padx=8, pady=(0, 8))

        # Restart hint (shown after enable/disable/install)
        self._restart_lbl = ctk.CTkLabel(
            self, text="", font=("Helvetica", 10, "bold"),
            text_color=YLW)
        self._restart_lbl.pack(fill="x", padx=16, pady=(0, 4))

        # Install section
        install_frame = ctk.CTkFrame(self, fg_color=BG2, corner_radius=6)
        install_frame.pack(fill="x", padx=16, pady=(4, 4))

        install_hdr = ctk.CTkFrame(install_frame, fg_color="transparent")
        install_hdr.pack(fill="x", padx=10, pady=(8, 4))

        self._install_title = ctk.CTkLabel(
            install_hdr, text=self.T("pluginmgr_install"),
            font=("Helvetica", 11, "bold"), text_color=FG)
        self._install_title.pack(side="left")

        self._install_hint = ctk.CTkLabel(
            install_frame, text=self.T("pluginmgr_install_hint"),
            font=("Helvetica", 9), text_color=FG2)
        self._install_hint.pack(fill="x", padx=10, pady=(0, 4))

        input_row = ctk.CTkFrame(install_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=(0, 8))

        self._install_entry = ctk.CTkEntry(
            input_row, placeholder_text=self.T("pluginmgr_install_url"),
            fg_color=BG3, border_color=BORDER, text_color=FG,
            font=("Helvetica", 10), height=28)
        self._install_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._browse_btn = ctk.CTkButton(
            input_row, text=self.T("pluginmgr_install_browse"),
            font=("Helvetica", 9), fg_color=BG3, hover_color=BORDER,
            text_color=FG2, height=28, width=70, corner_radius=4,
            command=self._browse_folder)
        self._browse_btn.pack(side="left", padx=(0, 4))

        self._install_btn = ctk.CTkButton(
            input_row, text=self.T("pluginmgr_install_btn"),
            font=("Helvetica", 10, "bold"),
            fg_color=BLUE, hover_color="#0284c7", text_color=FG,
            height=28, width=80, corner_radius=4,
            command=self._do_install)
        self._install_btn.pack(side="left")

        self._install_status = ctk.CTkLabel(
            install_frame, text="", font=("Helvetica", 9), text_color=FG2)
        self._install_status.pack(fill="x", padx=10, pady=(0, 6))

        # More plugins link
        self._more_lbl = ctk.CTkLabel(
            self, text=self.T("pluginmgr_more"),
            font=("Helvetica", 9), text_color=FG2)
        self._more_lbl.pack(fill="x", padx=16, pady=(2, 10))

        self._populate()

    def _populate(self):
        """Build one card per discovered plugin."""
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._rows.clear()

        pm = self._app._plugin_manager
        manifests = pm._manifests

        if not manifests:
            ctk.CTkLabel(
                self._list_frame, text=self.T("pluginmgr_empty"),
                font=("Helvetica", 12), text_color=FG2
            ).pack(pady=40)
            self._count_lbl.configure(text="")
            return

        for pid in sorted(manifests.keys()):
            info = manifests[pid]
            self._build_card(pid, info)

        total = len(manifests)
        active = sum(1 for p in manifests if pm.is_loaded(p))
        self._count_lbl.configure(
            text=self.T("pluginmgr_count", total=total, active=active))

    def _build_card(self, pid, info):
        pm = self._app._plugin_manager
        disabled = pm.is_disabled(pid)
        loaded = pm.is_loaded(pid)
        error = pm.get_error(pid)
        is_open = pid in self._expanded

        # Accent color
        if disabled:
            accent = FG2
        elif error:
            accent = RED
        else:
            accent = GRN

        # Card — use border_color for accent
        card = ctk.CTkFrame(self._list_frame, fg_color=BG3, corner_radius=6,
                            border_width=2, border_color=accent)
        card.pack(fill="x", padx=4, pady=3)

        # ── Header (always visible) ──────────────────────────────────────────
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=(8, 10), pady=(6, 6))

        # Expand arrow
        arrow = "\u25BC" if is_open else "\u25B6"
        arrow_lbl = ctk.CTkLabel(
            hdr, text=arrow, font=("Helvetica", 9), text_color=FG2,
            width=14, cursor="hand2")
        arrow_lbl.pack(side="left", padx=(0, 4))

        # Plugin icon
        icon_img = self._load_icon(pid, info)
        if icon_img:
            icon_lbl = ctk.CTkLabel(hdr, image=icon_img, text="", cursor="hand2")
            icon_lbl.pack(side="left", padx=(0, 6))

        # Name + version
        name = info.get("name", pid)
        ver = info.get("version", "")
        name_lbl = ctk.CTkLabel(
            hdr, text=name, font=("Helvetica", 12, "bold"),
            text_color=FG, cursor="hand2")
        name_lbl.pack(side="left")

        if ver:
            ver_lbl = ctk.CTkLabel(
                hdr, text=f"  v{ver}", font=("Helvetica", 10),
                text_color=FG2, cursor="hand2")
            ver_lbl.pack(side="left")

        # Type badges inline (compact, always visible)
        ptypes = info.get("type", "")
        if isinstance(ptypes, str):
            ptypes = [ptypes] if ptypes else []
        for ptype in ptypes:
            fg_c, bg_c = _TYPE_COLORS.get(ptype, (FG2, BG2))
            badge = ctk.CTkLabel(
                hdr, text=ptype,
                font=("Helvetica", 8, "bold"), text_color=fg_c,
                fg_color=bg_c, corner_radius=6,
                height=16, padx=3, cursor="hand2")
            badge.pack(side="left", padx=(6, 0))

        # Toggle button (always visible, right side)
        if disabled:
            btn_text = self.T("pluginmgr_enable")
            btn_color = GRN
            btn_hover = "#16a34a"
            btn_cmd = lambda p=pid: self._enable(p)
        else:
            btn_text = self.T("pluginmgr_disable")
            btn_color = RED
            btn_hover = "#b91c1c"
            btn_cmd = lambda p=pid: self._disable(p)

        toggle_btn = ctk.CTkButton(
            hdr, text=btn_text, font=("Helvetica", 10, "bold"),
            fg_color=btn_color, hover_color=btn_hover, text_color=FG,
            height=24, width=80, corner_radius=4,
            command=btn_cmd)
        toggle_btn.pack(side="right", padx=(8, 0))

        # ── Detail area (only when expanded) ──────────────────────────────────
        if is_open:
            detail = ctk.CTkFrame(card, fg_color="transparent")
            detail.pack(fill="x", padx=(8, 10), pady=(0, 6))
            self._fill_detail(detail, info, error)

        # ── Click binding for expand/collapse ─────────────────────────────────
        def toggle_expand(_e=None, p=pid):
            if p in self._expanded:
                self._expanded.discard(p)
            else:
                self._expanded.add(p)
            self._populate()

        # Bind click on all header widgets (not the toggle button)
        for w in (arrow_lbl, name_lbl, hdr):
            w.bind("<Button-1>", toggle_expand)
        if icon_img:
            icon_lbl.bind("<Button-1>", toggle_expand)
        if ver:
            ver_lbl.bind("<Button-1>", toggle_expand)
        for child in hdr.winfo_children():
            if child is not toggle_btn:
                child.bind("<Button-1>", toggle_expand)

        self._rows[pid] = {"card": card, "toggle": toggle_btn}

    def _fill_detail(self, parent, info, error):
        """Build the expanded detail content."""
        # Description
        desc = info.get("description", "")
        if desc:
            ctk.CTkLabel(
                parent, text=desc, font=("Helvetica", 10),
                text_color=FG2, anchor="w", justify="left"
            ).pack(fill="x", pady=(0, 4))

        # Help text
        help_text = info.get("help", "")
        if help_text:
            help_frame = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=4)
            help_frame.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(
                help_frame, text=f"\u2139  {help_text}",
                font=("Helvetica", 9), text_color=FG,
                anchor="w", justify="left", wraplength=400
            ).pack(fill="x", padx=8, pady=4)

        # Author
        author = info.get("author", "")
        if author:
            ctk.CTkLabel(
                parent, text=f"Author: {author}",
                font=("Helvetica", 9), text_color=FG2, anchor="w"
            ).pack(fill="x")

        # Error detail
        if error:
            ctk.CTkLabel(
                parent, text=error, font=("Helvetica", 9),
                text_color=RED, anchor="w", wraplength=400, justify="left"
            ).pack(fill="x", pady=(4, 0))

    def _load_icon(self, pid, info):
        """Load icon.png from plugin folder if it exists. Returns CTkImage or None."""
        if pid in self._icon_cache:
            return self._icon_cache[pid]
        pdir = info.get("_path", "")
        icon_path = os.path.join(pdir, "icon.png")
        if not os.path.isfile(icon_path):
            self._icon_cache[pid] = None
            return None
        try:
            pil_img = Image.open(icon_path).resize((28, 28), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                   size=(28, 28))
            self._icon_cache[pid] = ctk_img
            return ctk_img
        except Exception:
            self._icon_cache[pid] = None
            return None

    # ── Actions ───────────────────────────────────────────────────────────────

    def _enable(self, pid):
        pm = self._app._plugin_manager
        pm.enable_plugin(pid)
        info = pm._manifests.get(pid, {})
        ptypes = info.get("type", "")
        if isinstance(ptypes, str):
            ptypes = [ptypes]
        if "panel" in ptypes:
            self._restart_lbl.configure(text=self.T("pluginmgr_restart"))
        self._populate()

    def _disable(self, pid):
        pm = self._app._plugin_manager

        if pid in self._app._panels:
            self._app._panels[pid].pack_forget()
            del self._app._panels[pid]
        if pid in self._app._plugin_sw_btns:
            self._app._plugin_sw_btns[pid].destroy()
            del self._app._plugin_sw_btns[pid]

        pm.disable_plugin(pid)
        self._restart_lbl.configure(text=self.T("pluginmgr_restart"))
        self._populate()

    # ── Install ──────────────────────────────────────────────────────────────

    def _browse_folder(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select plugin folder")
        if path:
            self._install_entry.delete(0, "end")
            self._install_entry.insert(0, path)

    def _do_install(self):
        src = self._install_entry.get().strip()
        if not src:
            return
        self._install_btn.configure(state="disabled")
        self._install_status.configure(text="Installing...", text_color=YLW)

        if os.path.isdir(src):
            # Local folder
            self._install_from_folder(src)
        elif "github.com" in src:
            # GitHub URL — download in background
            threading.Thread(target=self._install_from_github, args=(src,),
                             daemon=True).start()
        else:
            self._install_btn.configure(state="normal")
            self._install_status.configure(
                text=self.T("pluginmgr_install_fail", err="Not a folder or GitHub URL"),
                text_color=RED)

    def _install_from_folder(self, src):
        """Install plugin from a local folder."""
        try:
            manifest_path = os.path.join(src, "plugin.json")
            if not os.path.isfile(manifest_path):
                self._install_status.configure(
                    text=self.T("pluginmgr_install_fail", err="No plugin.json found"),
                    text_color=RED)
                self._install_btn.configure(state="normal")
                return

            with open(manifest_path) as f:
                manifest = json.load(f)
            pid = manifest.get("id", "")
            if not pid:
                self._install_status.configure(
                    text=self.T("pluginmgr_install_fail", err="No id in plugin.json"),
                    text_color=RED)
                self._install_btn.configure(state="normal")
                return

            dest = os.path.join(_PLUGINS_DIR, pid)
            if os.path.exists(dest):
                # Overwrite existing (update)
                shutil.rmtree(dest)

            shutil.copytree(src, dest)
            # Remove __pycache__ if copied
            cache = os.path.join(dest, "__pycache__")
            if os.path.isdir(cache):
                shutil.rmtree(cache)

            self._install_status.configure(
                text=self.T("pluginmgr_install_ok"), text_color=GRN)
            self._restart_lbl.configure(text=self.T("pluginmgr_restart"))
            self._install_btn.configure(state="normal")

            # Re-discover to show the new plugin in the list
            self._app._plugin_manager.discover()
            self._populate()

        except Exception as e:
            self._install_status.configure(
                text=self.T("pluginmgr_install_fail", err=str(e)),
                text_color=RED)
            self._install_btn.configure(state="normal")

    def _install_from_github(self, url):
        """Download plugin from GitHub and install. Runs in background thread."""
        try:
            # Convert GitHub URL to zip download URL
            # Supports: github.com/user/repo/tree/branch/path/to/plugin
            #           github.com/user/repo
            url = url.rstrip("/")
            if "github.com" not in url:
                raise ValueError("Not a GitHub URL")

            # Parse owner/repo and optional path
            parts = url.split("github.com/", 1)[1].split("/")
            owner = parts[0]
            repo = parts[1] if len(parts) > 1 else ""
            branch = "main"
            subpath = ""

            if len(parts) > 3 and parts[2] == "tree":
                branch = parts[3]
                subpath = "/".join(parts[4:]) if len(parts) > 4 else ""

            # Download repo as zip
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
            tmp = tempfile.mkdtemp()
            zip_path = os.path.join(tmp, "repo.zip")

            req = urllib.request.Request(zip_url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(zip_path, "wb") as f:
                    f.write(resp.read())

            # Extract
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp)

            # Find the plugin folder
            extracted_root = os.path.join(tmp, f"{repo}-{branch}")
            if subpath:
                plugin_dir = os.path.join(extracted_root, subpath)
            else:
                # Look for plugin.json in root or first subfolder
                if os.path.isfile(os.path.join(extracted_root, "plugin.json")):
                    plugin_dir = extracted_root
                else:
                    # Check subfolders
                    plugin_dir = None
                    for d in os.listdir(extracted_root):
                        candidate = os.path.join(extracted_root, d)
                        if os.path.isdir(candidate) and os.path.isfile(
                                os.path.join(candidate, "plugin.json")):
                            plugin_dir = candidate
                            break
                    if not plugin_dir:
                        raise FileNotFoundError("No plugin.json found in repository")

            # Install from the found folder
            self.after(0, lambda: self._install_from_folder(plugin_dir))

            # Cleanup temp dir after a delay
            def _cleanup():
                try:
                    shutil.rmtree(tmp, ignore_errors=True)
                except Exception:
                    pass
            self.after(5000, _cleanup)

        except Exception as e:
            self.after(0, lambda: [
                self._install_status.configure(
                    text=self.T("pluginmgr_install_fail", err=str(e)),
                    text_color=RED),
                self._install_btn.configure(state="normal")
            ])

    # ── i18n ──────────────────────────────────────────────────────────────────

    def apply_lang(self):
        self._title_lbl.configure(text=self.T("pluginmgr_title"))
        self._hint_lbl.configure(text=self.T("pluginmgr_hint"))
        self._install_title.configure(text=self.T("pluginmgr_install"))
        self._install_hint.configure(text=self.T("pluginmgr_install_hint"))
        self._install_btn.configure(text=self.T("pluginmgr_install_btn"))
        self._browse_btn.configure(text=self.T("pluginmgr_install_browse"))
        self._more_lbl.configure(text=self.T("pluginmgr_more"))
        self._populate()
