EVENT_TO_STATE = {
    "SessionStart": "red",  # freshly opened = idle, not working; goes green on first prompt
    "UserPromptSubmit": "green",
    "PreToolUse": "green",
    "PostToolUse": "green",
    "Notification": "yellow",
    "Stop": "red",
    "SessionEnd": "delete",
}

GRAY_AFTER = 3600  # a red session older than this displays as gray

EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴", "gray": "💀"}
WORD = {"green": "working", "yellow": "needs you", "red": "done", "gray": "done"}
TITLE_ORDER = ["green", "yellow", "red", "gray"]  # menu bar count order
URGENCY = {"yellow": 0, "red": 1, "green": 2, "gray": 3}  # dropdown sort order


def event_to_state(event_name):
    """Map a hook event name to a state, 'delete', or None if unhandled."""
    return EVENT_TO_STATE.get(event_name)


def display_state(session, now):
    """Effective color for a session, applying the gray-staleness rule."""
    if session["state"] == "red" and now - session["updated"] > GRAY_AFTER:
        return "gray"
    return session["state"]


def format_age(seconds):
    """Human relative age from `now - updated` seconds."""
    if seconds < 45:
        return "just now"
    if seconds < 3600:
        return f"{round(seconds / 60)}m"
    return "1h+"


def dominant_state(sessions, now):
    """Single most-urgent present state, or None when there are no sessions.

    Applies the gray-staleness rule, then picks by URGENCY (yellow > red >
    green > gray). Used to color a single-icon tray (Windows) where the full
    per-state count can't be shown as text.
    """
    states = [display_state(s, now) for s in sessions]
    if not states:
        return None
    return min(states, key=lambda s: URGENCY[s])


def build_view(sessions, now):
    """Pure transform: sessions -> (menu bar title, sorted row strings)."""
    display = [(display_state(s, now), s) for s in sessions]

    counts = {}
    for state, _ in display:
        counts[state] = counts.get(state, 0) + 1
    parts = [f"{EMOJI[c]}{counts[c]}" for c in TITLE_ORDER if counts.get(c)]
    title = " ".join(parts) if parts else "🚦"

    display.sort(key=lambda ds: (URGENCY[ds[0]], -ds[1]["updated"]))
    rows = [
        f"{EMOJI[state]}  {s['project']} — {WORD[state]} ({format_age(now - s['updated'])})"
        for state, s in display
    ]
    return title, rows
