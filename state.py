EVENT_TO_STATE = {
    "SessionStart": "green",
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
