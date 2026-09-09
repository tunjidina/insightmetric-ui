"""Brand palette, as constants. The only design decision the public UI needs to know."""
ACCENT = "#2a78d6"      # signal, emphasis, first series
CONTRAST = "#d1682a"    # the one second hue, for two-sided comparisons only
FADED = "#dcdbd7"
UNKNOWN = "#b9b8b3"
INK_SOFT = "#52514e"

# Traffic-light bands for the recurrence badge.
def badge(p: float) -> str:
    if p >= 0.65:
        return f"🟢 Likely back tomorrow ({p:.0%})"
    if p >= 0.45:
        return f"🟡 Toss-up ({p:.0%})"
    return f"🔴 Likely to fade ({p:.0%})"
