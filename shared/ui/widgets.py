"""Reusable widgets built from the tokens.

Every widget here takes text that is already translated. Nothing in this module
reaches for the language files, because it has no app reference; the caller
passes `app.T("key")`. That keeps the components usable from a dialog, a panel
or a plugin without any of them importing the other.

No pictograms. Where a mark carries meaning it is drawn on a canvas (see
StatusDot) so it takes the text colour and is the same size on every system,
instead of being rendered from whatever emoji font happens to be installed.
"""
import tkinter as tk
import customtkinter as ctk

from shared.ui import tokens as T


# ── Containers ────────────────────────────────────────────────────────────────

class Card(ctk.CTkFrame):
    """A titled block of related controls. Put content into `body`, not into
    the card itself, so the padding stays in one place."""

    def __init__(self, parent, title=None, hint=None, **kw):
        kw.setdefault("fg_color", T.SURFACE)
        kw.setdefault("corner_radius", T.RADIUS)
        kw.setdefault("border_width", T.BORDER_W)
        kw.setdefault("border_color", T.LINE)
        super().__init__(parent, **kw)

        self._head = None
        if title:
            self._head = ctk.CTkFrame(self, fg_color="transparent")
            self._head.pack(fill="x", padx=T.S4, pady=(T.S3, 0))
            ctk.CTkLabel(self._head, text=title, font=T.font(T.TEXT_XS, bold=True),
                         text_color=T.FG, anchor="w").pack(side="left")
            if hint:
                self.hint_label = ctk.CTkLabel(
                    self._head, text=hint, font=T.font(T.TEXT_XS),
                    text_color=T.FG_FAINT, anchor="e")
                self.hint_label.pack(side="right")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=T.S4,
                       pady=(T.S3 if title else T.S4, T.S4))

    def set_hint(self, text):
        """Update the right-hand hint of the card header, if it has one."""
        if getattr(self, "hint_label", None) is not None:
            self.hint_label.configure(text=text)


class Toolbar(ctk.CTkFrame):
    """A row of controls above a work surface. Pack primary actions with
    side="right" so they sit at the end regardless of how many secondary
    ones are added later."""

    def __init__(self, parent, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)


class SectionLabel(ctk.CTkLabel):
    """Uppercase eyebrow above a group. The only place letter spacing is used,
    and the only place TEXT_XS is allowed outside metadata."""

    def __init__(self, parent, text="", **kw):
        kw.setdefault("font", T.font(T.TEXT_XS, bold=True))
        kw.setdefault("text_color", T.FG_FAINT)
        kw.setdefault("anchor", "w")
        super().__init__(parent, text=text.upper(), **kw)


# ── Buttons ───────────────────────────────────────────────────────────────────

def _button(parent, text, command, fg, hover, text_color, **kw):
    kw.setdefault("height", T.CTRL_H)
    kw.setdefault("corner_radius", T.RADIUS_SM)
    kw.setdefault("font", T.font(T.TEXT_XS, bold=True))
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=fg, hover_color=hover, text_color=text_color, **kw)


def PrimaryButton(parent, text, command=None, **kw):
    """The one action a screen is about. At most one per screen."""
    return _button(parent, text, command, T.ACCENT, T.ACCENT_HOVER, T.ACCENT_TEXT, **kw)


def GhostButton(parent, text, command=None, **kw):
    """Everything else. Outlined, so it never competes with the primary."""
    kw.setdefault("border_width", T.BORDER_W)
    kw.setdefault("border_color", T.LINE)
    return _button(parent, text, command, "transparent", T.HOVER, T.FG_DIM, **kw)


def DangerButton(parent, text, command=None, **kw):
    """Destructive. Outlined here, filled only inside the confirmation."""
    kw.setdefault("border_width", T.BORDER_W)
    kw.setdefault("border_color", T.DANGER)
    return _button(parent, text, command, "transparent", T.DANGER_HOVER, T.DANGER, **kw)


# ── State ─────────────────────────────────────────────────────────────────────

class StatusDot(tk.Canvas):
    """A drawn state mark, not a character. `state` is one of ok, warn, bad,
    off. Drawn so it cannot turn into a missing-glyph box on a system without
    an emoji font, and so it stays the same size at every font scaling."""

    _COLORS = {"ok": T.OK, "warn": T.WARN, "bad": T.DANGER, "off": T.LINE}

    def __init__(self, parent, state="off", size=8, bg=None, **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0,
                         bd=0, bg=bg or T.SURFACE, **kw)
        self._size = size
        self._item = self.create_oval(1, 1, size - 1, size - 1,
                                      fill=self._COLORS["off"], outline="")
        self.set_state(state)

    def set_state(self, state):
        self.itemconfigure(self._item, fill=self._COLORS.get(state, T.LINE))


class StatusPill(ctk.CTkFrame):
    """Dot plus one word: connected, busy, not ready. Reads at a glance and
    survives translation, which a coloured square alone does not."""

    def __init__(self, parent, text="", state="off", **kw):
        kw.setdefault("fg_color", T.SURFACE_2)
        kw.setdefault("corner_radius", 999)
        super().__init__(parent, **kw)
        self._dot = StatusDot(self, state=state, size=7, bg=T.SURFACE_2)
        self._dot.pack(side="left", padx=(T.S2, T.S1), pady=T.S1)
        self._label = ctk.CTkLabel(self, text=text, font=T.font(T.TEXT_XS),
                                   text_color=T.FG_DIM)
        self._label.pack(side="left", padx=(0, T.S2))

    def set(self, text=None, state=None):
        if text is not None:
            self._label.configure(text=text)
        if state is not None:
            self._dot.set_state(state)


class Field(ctk.CTkFrame):
    """Label above an entry. `var` is optional; without one the widget keeps
    its own StringVar, reachable through .get() and .set()."""

    def __init__(self, parent, label="", var=None, placeholder="", width=200, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        self.var = var if var is not None else tk.StringVar()
        if label:
            ctk.CTkLabel(self, text=label, font=T.font(T.TEXT_XS),
                         text_color=T.FG_DIM, anchor="w").pack(fill="x", pady=(0, T.S1))
        self.entry = ctk.CTkEntry(
            self, textvariable=self.var, width=width, height=T.CTRL_H,
            font=T.font(T.TEXT_XS), fg_color=T.SURFACE_2, text_color=T.FG,
            border_color=T.LINE, border_width=T.BORDER_W,
            corner_radius=T.RADIUS_SM, placeholder_text=placeholder)
        self.entry.pack(fill="x")

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)


# ── Dialogs ───────────────────────────────────────────────────────────────────

class _ModalBase(ctk.CTkToplevel):
    """Shared plumbing for our own modals: centred on the parent, Escape
    closes, the parent is blocked while it is open, and the result is read
    from .result after the call returns."""

    def __init__(self, parent, title=""):
        super().__init__(parent)
        self.result = None
        self._parent = parent
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=T.BG)
        try:
            self.transient(parent)
        except Exception:
            pass
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _cancel(self):
        self.result = None
        self._close()

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _run(self):
        """Centre on the parent, take the grab, block until closed."""
        self.update_idletasks()
        try:
            px = self._parent.winfo_rootx() + self._parent.winfo_width() // 2
            py = self._parent.winfo_rooty() + self._parent.winfo_height() // 2
            self.geometry(f"+{px - self.winfo_width() // 2}"
                          f"+{py - self.winfo_height() // 2}")
        except Exception:
            pass
        # Grabbing before the window is mapped fails on X11, hence the delay.
        self.after(20, self._take_grab)
        self.wait_window()
        return self.result

    def _take_grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass


class ConfirmDialog(_ModalBase):
    """Yes/no question in our own language instead of the system's message box.

    `danger=True` fills the confirming button red: that is the one place a
    filled destructive colour is allowed, because at that point the user is
    being asked to confirm exactly that.
    """

    def __init__(self, parent, title, message, ok_text, cancel_text=None,
                 danger=False, detail=None):
        super().__init__(parent, title)

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=T.S5, pady=T.S5)

        # The window manager already shows `title`. Repeating it inside is the
        # same duplicated-chrome problem the redesign is meant to remove, so
        # the question itself is the prominent text here.
        ctk.CTkLabel(wrap, text=message, font=T.font(T.TEXT_SM, bold=True),
                     text_color=T.FG, anchor="w", justify="left",
                     wraplength=380).pack(fill="x")
        if detail:
            box = ctk.CTkFrame(wrap, fg_color=T.SURFACE, corner_radius=T.RADIUS_SM,
                               border_width=T.BORDER_W, border_color=T.LINE)
            box.pack(fill="x", pady=(T.S3, 0))
            ctk.CTkLabel(box, text=detail, font=T.font(T.TEXT_XS),
                         text_color=T.FG_DIM, anchor="w", justify="left",
                         wraplength=356).pack(fill="x", padx=T.S3, pady=T.S3)

        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", pady=(T.S5, 0))
        if danger:
            confirm = _button(row, ok_text, self._ok, T.DANGER, T.DANGER_HOVER,
                              T.DANGER_TEXT, width=110)
        else:
            confirm = PrimaryButton(row, ok_text, self._ok, width=110)
        confirm.pack(side="right")
        # A statement (show_error) passes no cancel text and gets one button.
        if cancel_text:
            GhostButton(row, cancel_text, self._cancel,
                        width=100).pack(side="right", padx=(0, T.S2))

        self.bind("<Return>", lambda _e: self._ok())
        self._run()

    def _ok(self):
        self.result = True
        self._close()


class PromptDialog(_ModalBase):
    """One line of text input. Replaces CTkInputDialog, which brings its own
    styling and its own English button labels."""

    def __init__(self, parent, title, message, ok_text, cancel_text,
                 initial="", placeholder=""):
        super().__init__(parent, title)

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=T.S5, pady=T.S5)

        # Same rule as ConfirmDialog: no second copy of the window title.
        if message:
            ctk.CTkLabel(wrap, text=message, font=T.font(T.TEXT_SM, bold=True),
                         text_color=T.FG, anchor="w", justify="left",
                         wraplength=340).pack(fill="x")

        self._field = Field(wrap, placeholder=placeholder, width=340)
        self._field.pack(fill="x", pady=(T.S3, 0))
        self._field.set(initial)

        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", pady=(T.S5, 0))
        PrimaryButton(row, ok_text, self._ok, width=110).pack(side="right")
        GhostButton(row, cancel_text, self._cancel, width=100).pack(side="right", padx=(0, T.S2))

        self.bind("<Return>", lambda _e: self._ok())
        self.after(60, self._focus_entry)
        self._run()

    def _focus_entry(self):
        try:
            self._field.entry.focus_set()
            self._field.entry.select_range(0, "end")
        except Exception:
            pass

    def _ok(self):
        self.result = self._field.get().strip()
        self._close()


# ── Convenience ───────────────────────────────────────────────────────────────

def ask_yes_no(parent, title, message, ok_text, cancel_text, danger=False,
               detail=None):
    """True if confirmed, False otherwise. Never raises: a dialog that cannot
    open must not take an action with it, so it answers False."""
    try:
        return bool(ConfirmDialog(parent, title, message, ok_text, cancel_text,
                                  danger=danger, detail=detail).result)
    except Exception:
        return False


def ask_text(parent, title, message, ok_text, cancel_text, initial="", placeholder=""):
    """The entered string, or None when cancelled."""
    try:
        return PromptDialog(parent, title, message, ok_text, cancel_text,
                            initial=initial, placeholder=placeholder).result
    except Exception:
        return None


def show_error(parent, title, message, ok_text):
    """A statement, not a question: one button, same shape as the confirmation
    so the two do not look like different products."""
    try:
        ConfirmDialog(parent, title, message, ok_text, cancel_text=None)
    except Exception:
        pass
