"""Design tokens: the only place a colour, a font size or a spacing step is
defined.

The values are the ones the app already uses, they were just spread across 835
inline arguments in nine files with no rule about which one meant what. The
rule is here now:

    ACCENT   selected and clickable, and never more than one filled accent
             action on a screen
    OK       a state that is good: connected, saved, done. Never a button fill
    WARN     needs attention: firmware old, device busy, action without target
    DANGER   destructive: delete, reset. Outline first, filled only inside the
             confirmation itself

Surfaces come in three levels and no more: BG for the ground, SURFACE for a
card, SURFACE_2 for an input or a control sitting on that card. Text comes in
two, plus a third that is only for uppercase labels.

Sizes are a scale, not a free choice: four text sizes, five spacing steps.
Anything that does not fit the scale is a sign the layout is wrong, not that
the scale is too small.
"""

# ── Surfaces ──────────────────────────────────────────────────────────────────

BG        = "#0d0d14"   # window ground
SURFACE   = "#16161f"   # card, panel, dialog body
SURFACE_2 = "#1f1f2e"   # input, segmented control, tile
LINE      = "#272739"   # 1px separators and control borders

# ── Text ──────────────────────────────────────────────────────────────────────

FG       = "#e8e8ff"    # primary text
FG_DIM   = "#9090c0"    # secondary text, labels, help
FG_FAINT = "#63638a"    # uppercase eyebrows, disabled, metadata

# ── Meaning ───────────────────────────────────────────────────────────────────

ACCENT        = "#0ea5e9"
ACCENT_HOVER  = "#0284c7"
ACCENT_TEXT   = "#04121b"   # text on a filled accent surface
OK            = "#22c55e"
WARN          = "#f5c400"
DANGER        = "#ef4444"
DANGER_HOVER  = "#dc2626"
DANGER_TEXT   = "#ffffff"

HOVER      = "#222232"   # ghost button hover
HOVER_SOFT = "#2a2a3d"   # tile / row hover

# ── Type ──────────────────────────────────────────────────────────────────────
# Four sizes. TEXT_XS is for uppercase labels and metadata only, never for
# anything the user has to read in a sentence.

FONT_FAMILY = "Helvetica"
TEXT_XS = 11
TEXT_SM = 13
TEXT_MD = 16
TEXT_LG = 22


def font(size=TEXT_SM, bold=False):
    """A tuple Tk accepts. Two weights, no italics, no third weight."""
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


# ── Spacing ───────────────────────────────────────────────────────────────────
# Every padx/pady in the app comes from this list. S3 is the default gap
# between two related controls, S4 the padding inside a card.

S1, S2, S3, S4, S5 = 4, 8, 12, 16, 24

# ── Shape ─────────────────────────────────────────────────────────────────────

RADIUS     = 7    # card, dialog
RADIUS_SM  = 5    # button, input, tile
CTRL_H     = 32   # standard control height
CTRL_H_SM  = 26   # compact control height (toolbars, rows)
BORDER_W   = 1
