"""Mountain Everest 60 panel for BaseCamp Linux."""
import os
import subprocess
import threading
import tkinter as tk
import customtkinter as ctk

from shared.ui_helpers import BG, BG2, BG3, FG, FG2, BLUE, GRN, RED, YLW, BORDER
from shared.config import (CONFIG_DIR, load_rgb_config, save_rgb_config,
                            _load_per_key_60, _save_per_key_60,
                            _load_presets_60, _save_presets_60)
from devices.everest60.controller import detect_model, PID_ANSI


def _hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


class Everest60Panel(ctk.CTkFrame):
    """Panel for Mountain Everest 60 / Everest 60 ISO keyboard."""

    VID = 0x3282
    PID = PID_ANSI

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self._app       = app
        self._connected = False
        self._sections  = []
        self._i18n      = []   # (widget, attr, key)

        pid, model = detect_model()
        self._model_name = model or "Everest 60"
        if pid:
            self.PID = pid

        self._build_ui()

    # ── i18n ─────────────────────────────────────────────────────────────────

    def T(self, key, **kw):
        return self._app._lang.get(key, key).format(**kw) if kw else self._app._lang.get(key, key)

    def _reg(self, widget, key, attr="text"):
        self._i18n.append((widget, attr, key))
        widget.configure(**{attr: self.T(key)})
        return widget

    def apply_lang(self):
        for widget, attr, key in self._i18n:
            try:
                widget.configure(**{attr: self.T(key)})
            except Exception:
                pass
        # Widgets whose text takes a format argument or drives a dropdown aren't
        # part of the simple (widget, attr, key) table — refresh them by hand.
        if hasattr(self, "_rgb_build_lbl"):
            try:
                self._rgb_build_lbl.configure(
                    text=self.T("rgb_build_label", ver=self._rgb_build_ver))
            except Exception:
                pass
        if hasattr(self, "_rgb_cmode_menu"):
            try:
                cur = self._cmode_from_label.get(self._rgb_cmode_var.get(), "dual")
                self._cmode_labels = {
                    "single":  self.T("rgb_cmode_single"),
                    "dual":    self.T("rgb_cmode_dual"),
                    "rainbow": self.T("rgb_cmode_rainbow"),
                }
                self._cmode_from_label = {v: k for k, v in self._cmode_labels.items()}
                self._rgb_cmode_var.set(self._cmode_labels.get(cur, self._cmode_labels["dual"]))
                self._rgb_update_controls()
            except Exception:
                pass

    # ── Command builder ───────────────────────────────────────────────────────

    def _cmd(self, *args):
        return self._app._cmd_for_device("everest60", *args)

    def _run_async(self, cmd, on_done=None):
        def _worker():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                ok = r.returncode == 0 and r.stdout.strip() == "ok"
                if on_done:
                    self.after(0, lambda: on_done(ok, r.stdout.strip()))
            except Exception as e:
                if on_done:
                    self.after(0, lambda e=e: on_done(False, str(e)))
        threading.Thread(target=_worker, daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Not-connected banner
        self._banner = ctk.CTkFrame(self, fg_color="#3b1515", corner_radius=6)
        self._banner_lbl = ctk.CTkLabel(
            self._banner,
            text=self.T("device_not_connected", model=self._model_name),
            font=("Helvetica", 11), text_color=RED)
        self._banner_lbl.pack(pady=8, padx=16)
        if not self._connected:
            self._banner.pack(fill="x", padx=12, pady=(8, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True, pady=(4, 0))

        self._build_rgb_section(scroll)
        self._build_side_leds_section(scroll)
        # Custom RGB is now the "Custom" entry in the effect dropdown (#34) — no
        # separate section.

        self._app.update_idletasks()
        for s in self._sections:
            s.measure()

    def _build_rgb_section(self, scroll):
        title = f"{self.T('rgb_title')} — {self._model_name}"
        s = _Section(scroll, self._app, "💡", title)
        self._sections.append(s)
        self._rgb_section = s
        self._build_rgb_content(s.content)

    def _build_rgb_content(self, parent):
        # Effect capability table (issue #32). Instead of separate "… Rainbow"
        # entries, each effect declares which colour modes it supports and a
        # single Color-mode dropdown offers only those — this is what the
        # original Base Camp does and it stops the old "rainbow page sticks"
        # confusion. dir_kind is None / "wave" (4-way) / "tornado" (2-way).
        #   (cli_sub, colour_modes, has_speed, has_bri, dir_kind)
        _RGB_EFFECTS = [
            ("Static",    "static",   ("single",),                 False, True,  None),
            ("Breathing", "breathing",("single", "dual", "rainbow"), True, True,  None),
            ("Wave",      "wave",     ("single", "dual", "rainbow"), True, True,  "wave"),
            ("Tornado",   "tornado",  ("single", "rainbow"),        True, True,  "tornado"),
            ("Reactive",  "reactive", ("dual",),                    True, True,  None),
            ("Matrix",    "matrix",   ("dual",),                    True, True,  None),  # #38
            ("Yeti",      "yeti",     ("dual",),                    True, True,  None),
            # "Custom" (issue #34): opens the per-key editor; no effect controls.
            ("Custom",    "custom",   (),                           False, False, None),
            ("Off",       "off",      (),                           False, False, None),
        ]
        self._rgb_effect_map = {
            name: (sub, modes, hs, hb, dk)
            for name, sub, modes, hs, hb, dk in _RGB_EFFECTS
        }
        _rgb_names = [e[0] for e in _RGB_EFFECTS]
        # Color-mode display labels ↔ internal keys.
        self._cmode_labels = {
            "single":  self.T("rgb_cmode_single"),
            "dual":    self.T("rgb_cmode_dual"),
            "rainbow": self.T("rgb_cmode_rainbow"),
        }
        self._cmode_from_label = {v: k for k, v in self._cmode_labels.items()}

        # Effect row
        mode_row = ctk.CTkFrame(parent, fg_color="transparent")
        mode_row.pack(fill="x", padx=10, pady=(10, 2))
        self._reg(ctk.CTkLabel(mode_row, text="", font=("Helvetica", 11),
                               text_color=FG2), "rgb_mode_label").pack(side="left", padx=(0, 6))
        self._rgb_mode_var = tk.StringVar(value=_rgb_names[0])
        ctk.CTkOptionMenu(
            mode_row, variable=self._rgb_mode_var, values=_rgb_names,
            command=lambda _: self._on_rgb_mode_change(),
            fg_color=BG3, button_color=BG3, button_hover_color=BG2,
            text_color=FG, font=("Helvetica", 11), width=180, height=32
        ).pack(side="left")

        # Color-mode row (Single / Dual / Rainbow) — only shown when the effect
        # offers a choice (issue #32).
        self._rgb_cmode_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._reg(ctk.CTkLabel(self._rgb_cmode_row, text="", font=("Helvetica", 11),
                               text_color=FG2), "rgb_colormode_label").pack(side="left", padx=(0, 6))
        self._rgb_cmode_var = tk.StringVar(value=self._cmode_labels["dual"])
        self._rgb_cmode_menu = ctk.CTkOptionMenu(
            self._rgb_cmode_row, variable=self._rgb_cmode_var,
            values=list(self._cmode_labels.values()),
            command=lambda _: self._on_rgb_cmode_change(),
            fg_color=BG3, button_color=BG3, button_hover_color=BG2,
            text_color=FG, font=("Helvetica", 11), width=140, height=32)
        self._rgb_cmode_menu.pack(side="left")

        # Speed / brightness sliders
        def _slider(par, key, init):
            row = ctk.CTkFrame(par, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            self._reg(ctk.CTkLabel(row, text="", text_color=FG2,
                                   font=("Helvetica", 11), width=120, anchor="w"), key).pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=str(init), text_color=FG,
                                   font=("Helvetica", 11), width=30)
            val_lbl.pack(side="right")
            sl = ctk.CTkSlider(row, from_=0, to=100, number_of_steps=100,
                               fg_color=BG3, progress_color=BLUE,
                               button_color=BLUE, button_hover_color=BLUE,
                               width=180, height=16)
            sl.set(init)
            sl.pack(side="left", padx=(0, 4))
            sl.configure(command=lambda v, l=val_lbl: l.configure(text=str(int(v))))
            return sl, row

        self._rgb_speed_sl, self._rgb_speed_row = _slider(parent, "rgb_speed_label", 50)
        self._rgb_bri_sl,   self._rgb_bri_row   = _slider(parent, "rgb_brightness_label", 100)

        # Color pickers
        self._rgb_color_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._rgb_color_row.pack(fill="x", padx=10, pady=2)
        self._rgb_color1 = (255, 0, 0)
        self._rgb_color2 = (0, 0, 255)
        self._rgb_c1_lbl = self._reg(ctk.CTkLabel(
            self._rgb_color_row, text="", text_color=FG2,
            font=("Helvetica", 11)), "rgb_color1_label")
        self._rgb_c1_lbl.pack(side="left", padx=(0, 4))
        self._rgb_c1_btn = ctk.CTkButton(
            self._rgb_color_row, text="", width=40, height=28,
            fg_color=_hex(*self._rgb_color1), hover_color=_hex(*self._rgb_color1),
            corner_radius=4, command=lambda: self._pick_color(1))
        self._rgb_c1_btn.pack(side="left", padx=(0, 12))
        self._rgb_c2_lbl = self._reg(ctk.CTkLabel(
            self._rgb_color_row, text="", text_color=FG2,
            font=("Helvetica", 11)), "rgb_color2_label")
        self._rgb_c2_lbl.pack(side="left", padx=(0, 4))
        self._rgb_c2_btn = ctk.CTkButton(
            self._rgb_color_row, text="", width=40, height=28,
            fg_color=_hex(*self._rgb_color2), hover_color=_hex(*self._rgb_color2),
            corner_radius=4, command=lambda: self._pick_color(2))
        self._rgb_c2_btn.pack(side="left")

        # Direction picker
        dir_row = ctk.CTkFrame(parent, fg_color="transparent")
        dir_row.pack(fill="x", padx=10, pady=2)
        self._rgb_dir_row = dir_row
        self._reg(ctk.CTkLabel(dir_row, text="", text_color=FG2,
                               font=("Helvetica", 11)), "rgb_direction_label").pack(side="left", padx=(0, 6))
        self._dir_wave    = ["→ L→R", "↓ T→B", "← R→L", "↑ B→T"]
        self._dir_tornado = ["↻ CW", "↺ CCW"]
        self._rgb_dir_map = {"→ L→R": 0, "↓ T→B": 2, "← R→L": 4, "↑ B→T": 6,
                             "↻ CW": 0, "↺ CCW": 1}
        self._rgb_dir_var = tk.StringVar(value=self._dir_wave[0])
        self._rgb_dir_menu = ctk.CTkOptionMenu(
            dir_row, variable=self._rgb_dir_var, values=self._dir_wave,
            fg_color=BG3, button_color=BG3, button_hover_color=BG2,
            text_color=FG, font=("Helvetica", 11), width=120, height=28)
        self._rgb_dir_menu.pack(side="left")

        # Status + Apply
        self._rgb_status = ctk.CTkLabel(parent, text="", font=("Helvetica", 11),
                                        text_color=FG2, fg_color="transparent")
        self._rgb_status.pack(pady=(4, 0))
        self._rgb_apply_btn = self._reg(ctk.CTkButton(
            parent, text="", height=32, corner_radius=4,
            fg_color=BLUE, hover_color="#0884be", text_color=FG,
            font=("Helvetica", 11), command=self._apply_rgb), "rgb_apply")
        self._rgb_apply_btn.pack(fill="x", padx=10, pady=(4, 10))
        # Editor launcher, shown only when the "Custom" effect is selected (#34).
        self._rgb_custom_btn = self._reg(ctk.CTkButton(
            parent, text="", height=32, corner_radius=4,
            fg_color=BLUE, hover_color="#0884be", text_color=FG,
            font=("Helvetica", 11), command=self._open_custom_rgb), "custom_rgb_open")

        # Version line at the very bottom of the form (FransM's request in #32:
        # a build marker so screenshots/reports can be tied to a version).
        try:
            from gui import APP_VERSION as _ver
        except Exception:
            _ver = "?"
        self._rgb_build_lbl = ctk.CTkLabel(
            parent, text=self.T("rgb_build_label", ver=_ver),
            font=("Helvetica", 9), text_color=FG2, fg_color="transparent")
        self._rgb_build_ver = _ver  # refreshed in apply_lang (takes a format arg)

        # Restore saved settings
        saved = load_rgb_config()
        if saved.get("effect") in self._rgb_effect_map:
            self._rgb_mode_var.set(saved["effect"])
        if "speed" in saved:
            self._rgb_speed_sl.set(saved["speed"])
        if "brightness" in saved:
            self._rgb_bri_sl.set(saved["brightness"])
        if "color1" in saved:
            self._rgb_color1 = tuple(saved["color1"])
            h = _hex(*self._rgb_color1)
            self._rgb_c1_btn.configure(fg_color=h, hover_color=h)
        if "color2" in saved:
            self._rgb_color2 = tuple(saved["color2"])
            h = _hex(*self._rgb_color2)
            self._rgb_c2_btn.configure(fg_color=h, hover_color=h)
        if "direction" in saved:
            self._rgb_dir_var.set(saved["direction"])
        saved_cmode = saved.get("cmode")
        if saved_cmode in self._cmode_labels:
            self._rgb_cmode_var.set(self._cmode_labels[saved_cmode])

        self._rgb_update_controls()

    def _build_side_leds_section(self, scroll):
        """Side perimeter ring (44 LEDs) — single colour for now.

        Uses the custom-RGB protocol path under the hood, so the main keys
        are blanked when only side colour is applied. A future enhancement
        can fold this into the full custom-RGB editor.
        """
        s = _Section(scroll, self._app, "✨",
                     f"{self.T('side_leds_title')} — {self._model_name}")
        self._sections.append(s)
        self._side_leds_section = s

        row = ctk.CTkFrame(s.content, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(10, 2))
        self._reg(ctk.CTkLabel(
            row, text="", text_color=FG2,
            font=("Helvetica", 11)), "side_leds_color_label").pack(side="left", padx=(0, 4))
        self._side_led_color = (255, 0, 67)  # Mountain brand magenta default
        self._side_led_btn = ctk.CTkButton(
            row, text="", width=40, height=28,
            fg_color=_hex(*self._side_led_color),
            hover_color=_hex(*self._side_led_color),
            corner_radius=4, command=self._pick_side_color)
        self._side_led_btn.pack(side="left", padx=(0, 12))

        bri_row = ctk.CTkFrame(s.content, fg_color="transparent")
        bri_row.pack(fill="x", padx=10, pady=2)
        self._reg(ctk.CTkLabel(bri_row, text="", text_color=FG2,
                               font=("Helvetica", 11), width=120, anchor="w"),
                  "rgb_brightness_label").pack(side="left")
        val_lbl = ctk.CTkLabel(bri_row, text="100", text_color=FG,
                               font=("Helvetica", 11), width=30)
        val_lbl.pack(side="right")
        self._side_bri_sl = ctk.CTkSlider(
            bri_row, from_=0, to=100, number_of_steps=100,
            fg_color=BG3, progress_color=BLUE,
            button_color=BLUE, button_hover_color=BLUE,
            width=180, height=16)
        self._side_bri_sl.set(100)
        self._side_bri_sl.pack(side="left", padx=(0, 4))
        self._side_bri_sl.configure(
            command=lambda v, l=val_lbl: l.configure(text=str(int(v))))

        self._side_leds_status = ctk.CTkLabel(
            s.content, text="", font=("Helvetica", 11),
            text_color=FG2, fg_color="transparent")
        self._side_leds_status.pack(pady=(4, 0))

        self._reg(ctk.CTkButton(
            s.content, text="", height=32, corner_radius=4,
            fg_color=BLUE, hover_color="#0884be",
            text_color=FG, font=("Helvetica", 11),
            command=self._apply_side_leds), "side_leds_apply"
        ).pack(fill="x", padx=10, pady=(4, 10))

        self._reg(ctk.CTkLabel(
            s.content, text="",
            font=("Helvetica", 9), text_color=FG2,
            wraplength=380, justify="left"), "side_leds_hint"
        ).pack(fill="x", padx=10, pady=(0, 8))

    def _pick_side_color(self):
        from shared.ui_helpers import pick_color
        rgb = pick_color(self._app, initial_rgb=self._side_led_color,
                         title=self.T("color_picker_title"), show_brightness=False)
        if rgb is None:
            return
        self._side_led_color = rgb
        h = _hex(*rgb)
        self._side_led_btn.configure(fg_color=h, hover_color=h)

    def _apply_side_leds(self):
        import json as _j
        r, g, b = self._side_led_color
        bri = int(self._side_bri_sl.get())
        # Preserve the current main-key colours instead of blanking them: the
        # side ring can only be driven in custom mode, so we pull the last saved
        # per-key state and push it alongside the uniform ring in one write
        # (issue #4 follow-up — FransM: "the leds of the kbd are turned off").
        try:
            leds, _saved_side, _saved_bri = _load_per_key_60()
            leds = [list(c) for c in leds]
        except Exception:
            leds = []
        if not leds:
            # No saved per-key state — light the keys white instead of letting
            # the controller pad them black, so the keyboard never goes dark
            # (issue #4, FransM: "I really hate it when my kbd goes dark").
            leds = [[255, 255, 255]] * 64
        payload = _j.dumps({
            "leds": leds,
            "side": [[r, g, b]] * 44,
            "brightness": bri,
        })
        cmd = self._cmd("per-key-rgb", payload)
        try:
            subprocess.run(cmd, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self._side_leds_status.configure(
                text=self.T("side_leds_applied"), text_color=GRN)
        except subprocess.CalledProcessError as e:
            self._side_leds_status.configure(
                text=str(e.stderr.decode() if e.stderr else e), text_color=RED)

    def _open_custom_rgb(self):
        from shared.ui_helpers import CustomRGBWindow, _KB60_LAYOUT, _KB60_CANVAS_W, _KB60_CANVAS_H, _KB60_NUM_LEDS
        w = CustomRGBWindow(
            self._app,
            layout=_KB60_LAYOUT,
            canvas_w=_KB60_CANVAS_W,
            # Extra vertical space for the 44-LED side-ring strip below the keys.
            canvas_h=_KB60_CANVAS_H + 96,
            num_leds=_KB60_NUM_LEDS,
            has_side_leds=True,      # per-LED side ring painting (#4)
            num_side_leds=44,        # hw indices 126..169
            side_layout="strip",     # no per-edge ring geometry for the 60 yet
            has_numpad=False,
            has_persist=False,
            load_per_key=_load_per_key_60,
            save_per_key=_save_per_key_60,
            load_presets=_load_presets_60,
            save_presets=_save_presets_60,
            apply_cmd=lambda *a: self._app._cmd_for_device("everest60", *a),
        )
        w.lift()
        w.focus_force()

    def _available_cmodes(self, name):
        """Colour-mode keys the given effect supports (subset of single/dual/rainbow)."""
        return self._rgb_effect_map.get(name, ("", (), False, False, None))[1]

    def _current_cmode(self, name):
        """Effective colour mode: the dropdown choice if the effect offers it,
        else the effect's single supported mode (None for custom/off)."""
        modes = self._available_cmodes(name)
        if not modes:
            return None
        sel = self._cmode_from_label.get(self._rgb_cmode_var.get())
        return sel if sel in modes else modes[0]

    def _on_rgb_mode_change(self):
        """Effect changed: repopulate the colour-mode dropdown with the modes
        this effect supports (keeping the current choice if still valid),
        persist the effect (#34), then refresh which controls are shown."""
        name = self._rgb_mode_var.get()
        modes = self._available_cmodes(name)
        if modes:
            self._rgb_cmode_menu.configure(values=[self._cmode_labels[m] for m in modes])
            if self._cmode_from_label.get(self._rgb_cmode_var.get()) not in modes:
                self._rgb_cmode_var.set(self._cmode_labels[modes[0]])
        try:
            cfg = load_rgb_config()
            cfg["effect"] = name
            save_rgb_config(cfg)
        except Exception:
            pass
        self._rgb_update_controls()

    def _on_rgb_cmode_change(self):
        """Colour-mode changed — just refresh visibility (colour pickers)."""
        self._rgb_update_controls()

    def _rgb_update_controls(self):
        """Pack exactly the controls the selected (effect, colour-mode) uses, in
        a fixed top-to-bottom order, then re-measure the accordion.

        The previous implementation toggled rows via winfo_ismapped() + re-pack,
        which (a) appended re-shown rows to the bottom, scrambling order, and
        (b) left rows hidden inside the section's fixed measured height. That is
        what produced FransM's 'no speed on breathing', 'no speed/direction on
        wave' and 'rainbow page sticks' reports (#32/#39). Re-packing everything
        in canonical order and re-measuring fixes all three at the root."""
        name = self._rgb_mode_var.get()
        sub, modes, hs, hb, dk = self._rgb_effect_map.get(
            name, ("", (), False, False, None))
        cmode = self._current_cmode(name)

        # Forget every toggleable widget, then re-pack the visible ones in order.
        for w in (self._rgb_cmode_row, self._rgb_speed_row, self._rgb_bri_row,
                  self._rgb_color_row, self._rgb_dir_row, self._rgb_status,
                  self._rgb_apply_btn, self._rgb_custom_btn, self._rgb_build_lbl,
                  self._rgb_c1_lbl, self._rgb_c1_btn,
                  self._rgb_c2_lbl, self._rgb_c2_btn):
            w.pack_forget()

        show_c1 = cmode in ("single", "dual")
        show_c2 = cmode == "dual"

        if len(modes) >= 2:                       # only when there's a real choice
            self._rgb_cmode_row.pack(fill="x", padx=10, pady=2)
        if hs:
            self._rgb_speed_row.pack(fill="x", padx=10, pady=2)
        if hb:
            self._rgb_bri_row.pack(fill="x", padx=10, pady=2)
        if show_c1 or show_c2:
            if show_c1:
                self._rgb_c1_lbl.pack(side="left", padx=(0, 4))
                self._rgb_c1_btn.pack(side="left", padx=(0, 12))
            if show_c2:
                self._rgb_c2_lbl.pack(side="left", padx=(0, 4))
                self._rgb_c2_btn.pack(side="left")
            self._rgb_color_row.pack(fill="x", padx=10, pady=2)
        if dk is not None:
            self._rgb_dir_row.pack(fill="x", padx=10, pady=2)
            dirs = self._dir_tornado if dk == "tornado" else self._dir_wave
            self._rgb_dir_menu.configure(values=dirs)
            if self._rgb_dir_var.get() not in dirs:
                self._rgb_dir_var.set(dirs[0])

        self._rgb_status.pack(pady=(4, 0))
        if sub == "custom":
            self._rgb_custom_btn.pack(fill="x", padx=10, pady=(4, 10))
        elif sub:                                 # any real effect (incl. off)
            self._rgb_apply_btn.pack(fill="x", padx=10, pady=(4, 10))
        self._rgb_build_lbl.pack(pady=(0, 8))     # version line stays at the bottom

        self._remeasure_rgb_section()

    def _remeasure_rgb_section(self):
        """Recompute the RGB accordion's content height so a changed control set
        isn't clipped or bottom-padded by the previously measured height (#32)."""
        sec = getattr(self, "_rgb_section", None)
        if sec is None:
            return
        try:
            sec.measure()
        except Exception:
            pass

    def _pick_color(self, slot):
        from shared.ui_helpers import pick_color
        initial = self._rgb_color1 if slot == 1 else self._rgb_color2
        rgb = pick_color(self._app, initial_rgb=initial, title=self.T("color_picker_title"), show_brightness=False)
        if rgb is None:
            return
        h = _hex(*rgb)
        if slot == 1:
            self._rgb_color1 = rgb
            self._rgb_c1_btn.configure(fg_color=h, hover_color=h)
        else:
            self._rgb_color2 = rgb
            self._rgb_c2_btn.configure(fg_color=h, hover_color=h)

    def _build_rgb_command(self):
        """Translate the current UI selection into an everest60 `rgb` CLI command.

        Returns (cmd, save_dict). cmd is None for Custom (the editor applies it)
        and Off-less unknowns. Rainbow colour-mode routes to the `<effect>-rainbow`
        subcommand; single/dual pass a trailing colour-mode value (0/16)."""
        name = self._rgb_mode_var.get()
        sub, modes, hs, hb, dk = self._rgb_effect_map.get(
            name, ("off", (), False, False, None))
        cmode = self._current_cmode(name)
        speed = int(self._rgb_speed_sl.get())
        bri   = int(self._rgb_bri_sl.get())
        r1, g1, b1 = self._rgb_color1
        r2, g2, b2 = self._rgb_color2
        direction  = self._rgb_dir_map.get(self._rgb_dir_var.get(), 0)
        cm_val = 0 if cmode == "single" else 16   # COLOR_SINGLE / COLOR_DUAL

        save = {
            "effect": name, "cmode": cmode or "dual", "speed": speed,
            "brightness": bri, "color1": list(self._rgb_color1),
            "color2": list(self._rgb_color2), "direction": self._rgb_dir_var.get(),
        }

        if sub == "custom":
            return None, {"effect": name}
        if sub == "off":
            return self._cmd("rgb", "off"), save
        if sub == "static":
            return self._cmd("rgb", "static", str(r1), str(g1), str(b1), str(bri)), save
        if cmode == "rainbow" and sub in ("breathing", "wave", "tornado"):
            args = [f"{sub}-rainbow", str(bri), str(speed)]
            if dk is not None:
                args.append(str(direction))
            return self._cmd("rgb", *args), save
        if sub == "breathing":
            return self._cmd("rgb", "breathing", str(r1), str(g1), str(b1),
                             str(r2), str(g2), str(b2), str(bri), str(speed),
                             str(cm_val)), save
        if sub == "wave":
            return self._cmd("rgb", "wave", str(r1), str(g1), str(b1),
                             str(r2), str(g2), str(b2), str(bri), str(speed),
                             str(direction), str(cm_val)), save
        if sub == "tornado":
            return self._cmd("rgb", "tornado", str(r1), str(g1), str(b1),
                             str(bri), str(speed), str(direction)), save
        if sub in ("reactive", "matrix", "yeti"):
            return self._cmd("rgb", sub, str(r1), str(g1), str(b1),
                             str(r2), str(g2), str(b2), str(bri), str(speed)), save
        return None, None

    def _apply_rgb(self):
        cmd, save = self._build_rgb_command()
        if cmd is None:
            return
        if save:
            save_rgb_config(save)

        self._rgb_status.configure(text=self.T("rgb_applying"), text_color=YLW)

        def _done(ok, msg):
            self._rgb_status.configure(
                text=self.T("rgb_applied") if ok else f"{self.T('rgb_error')}: {msg[:40]}",
                text_color=GRN if ok else RED)
            self.after(3000, lambda: self._rgb_status.configure(text=""))

        self._run_async(cmd, _done)

    def apply_saved_rgb(self):
        """Re-push the saved lighting to the keyboard on connect/startup (#42):
        settings were persisted to rgb_settings.json but never sent, so the board
        kept its default lighting until the user pressed Apply. The widgets are
        already primed from the saved config at build time, so we reuse the same
        command builder. Custom mode replays its saved per-key map instead. Does
        nothing when nothing has been saved yet (don't clobber the board)."""
        try:
            saved = load_rgb_config()
            if not saved.get("effect"):
                return
            sub = self._rgb_effect_map.get(self._rgb_mode_var.get(), ("",))[0]
            if sub == "custom":
                self._apply_saved_custom()
                return
            cmd, _save = self._build_rgb_command()
            if cmd:
                self._run_async(cmd, None)
        except Exception:
            pass

    def _apply_saved_custom(self):
        """Replay the last per-key map for the Custom effect on connect (#42)."""
        import json as _j
        try:
            leds, side, bri = _load_per_key_60()
        except Exception:
            return
        if not leds:
            return
        payload = _j.dumps({
            "leds": [list(c) for c in leds],
            "side": [list(c) for c in side] if side else [],
            "brightness": int(bri),
        })
        self._run_async(self._cmd("per-key-rgb", payload), None)

    # ── Connection state ──────────────────────────────────────────────────────

    def set_connected(self, connected: bool):
        if connected == self._connected:
            return
        self._connected = connected
        if connected:
            self._banner.pack_forget()
            # Push the saved lighting now that the board is present (#42). Delay
            # a beat so the HID interface has finished enumerating before we open
            # it — otherwise the very first apply can race the device coming up.
            self.after(900, self.apply_saved_rgb)
        else:
            self._banner.pack(fill="x", padx=12, pady=(8, 4), before=self.winfo_children()[1])

    # ── CPU proc stubs (GUI expects these) ────────────────────────────────────

    def _stop_cpu_proc(self):
        return False

    def _start_cpu_auto(self):
        pass


# ── Accordion section ─────────────────────────────────────────────────────────

class _Section:
    def __init__(self, parent, app, icon, title):
        self._app       = app
        self._open      = False
        self._natural_h = 0

        self._outer = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self._outer.pack(fill="x", pady=2)

        self._header = ctk.CTkFrame(self._outer, fg_color=BG2, corner_radius=6, cursor="hand2")
        self._header.pack(fill="x")

        tk.Frame(self._header, bg=YLW, width=4).pack(side="left", fill="y")
        ctk.CTkLabel(self._header, text=icon, font=("Helvetica", 14),
                     text_color=YLW, width=30).pack(side="left", padx=(8, 4))
        self._title_lbl = ctk.CTkLabel(self._header, text=title,
                                       font=("Helvetica", 11, "bold"), text_color=FG, anchor="w")
        self._title_lbl.pack(side="left", fill="x", expand=True, padx=4, pady=12)
        self._chevron = ctk.CTkLabel(self._header, text="▶",
                                     font=("Helvetica", 10), text_color=FG2, width=24)
        self._chevron.pack(side="right", padx=(0, 12))

        self._content = ctk.CTkFrame(self._outer, fg_color=BG2, corner_radius=0, height=0)
        self._content.pack(fill="x", pady=(1, 0))
        self._content.pack_propagate(False)

        def _bind_all(w):
            w.bind("<Button-1>", self._toggle)
            for child in w.winfo_children():
                _bind_all(child)
        _bind_all(self._header)

    @property
    def content(self):
        return self._content

    def measure(self):
        self._content.pack_propagate(True)
        self._app.update_idletasks()
        self._natural_h = self._content.winfo_reqheight()
        self._content.pack_propagate(False)
        self._content.configure(height=self._natural_h if self._open else 0)

    def open(self):
        if self._open:
            return
        self._open = True
        self._chevron.configure(text="▼")
        if self._natural_h > 0:
            self._content.configure(height=self._natural_h)

    def _toggle(self, _=None):
        self.close() if self._open else self.open()

    def close(self):
        if not self._open:
            return
        self._open = False
        self._chevron.configure(text="▶")
        self._content.configure(height=0)
