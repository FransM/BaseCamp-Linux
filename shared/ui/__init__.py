"""Design system for BaseCamp Linux: tokens and reusable widgets.

`tokens` holds every colour, font size and spacing step the UI is allowed to
use. `widgets` builds the handful of components those tokens describe, so a
button is one call instead of eight keyword arguments repeated 134 times.

Nothing in here talks to a device or to the config; it is presentation only.
Import from the package, not from the modules:

    from shared.ui import PrimaryButton, Card, tokens as T
"""
from shared.ui import tokens
from shared.ui.tokens import (
    BG, SURFACE, SURFACE_2, LINE, FG, FG_DIM, FG_FAINT,
    ACCENT, ACCENT_HOVER, OK, WARN, DANGER, DANGER_HOVER,
    FONT_FAMILY, TEXT_XS, TEXT_SM, TEXT_MD, TEXT_LG,
    font, S1, S2, S3, S4, S5, RADIUS, RADIUS_SM, CTRL_H, CTRL_H_SM,
)
from shared.ui.widgets import (
    Card, SectionLabel, Toolbar, NavItem,
    PrimaryButton, GhostButton, DangerButton,
    StatusDot, StatusPill, Field, Toast, resolve_t,
    bind_dropdown_autoclose,
    ConfirmDialog, PromptDialog, ask_yes_no, ask_text, show_error,
)
from shared.ui.dropdown import (
    InlineDropdown, InlineMenu, install_inline_dropdown,
)

# Every option menu and combo box in the application opens its list inside the
# window from here on (#66). Done once, at import, so a panel does not have to
# ask for it and one added later is covered as well.
install_inline_dropdown()

__all__ = [
    "tokens",
    "BG", "SURFACE", "SURFACE_2", "LINE", "FG", "FG_DIM", "FG_FAINT",
    "ACCENT", "ACCENT_HOVER", "OK", "WARN", "DANGER", "DANGER_HOVER",
    "FONT_FAMILY", "TEXT_XS", "TEXT_SM", "TEXT_MD", "TEXT_LG", "font",
    "S1", "S2", "S3", "S4", "S5", "RADIUS", "RADIUS_SM", "CTRL_H", "CTRL_H_SM",
    "Card", "SectionLabel", "Toolbar", "NavItem",
    "PrimaryButton", "GhostButton", "DangerButton",
    "StatusDot", "StatusPill", "Field", "Toast", "resolve_t",
    "bind_dropdown_autoclose",
    "InlineDropdown", "InlineMenu", "install_inline_dropdown",
    "ConfirmDialog", "PromptDialog", "ask_yes_no", "ask_text", "show_error",
]
