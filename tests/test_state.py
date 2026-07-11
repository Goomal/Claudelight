from state import event_to_state, display_state, format_age


def test_event_to_state_mapping():
    assert event_to_state("SessionStart") == "green"
    assert event_to_state("UserPromptSubmit") == "green"
    assert event_to_state("PreToolUse") == "green"
    assert event_to_state("PostToolUse") == "green"
    assert event_to_state("Notification") == "yellow"
    assert event_to_state("Stop") == "red"
    assert event_to_state("SessionEnd") == "delete"
    assert event_to_state("PreCompact") is None


def test_display_state_gray_boundary():
    now = 10000
    assert display_state({"state": "red", "updated": now - 3599}, now) == "red"
    assert display_state({"state": "red", "updated": now - 3601}, now) == "gray"


def test_display_state_non_red_never_grays():
    now = 10000
    assert display_state({"state": "green", "updated": now - 999999}, now) == "green"
    assert display_state({"state": "yellow", "updated": now - 999999}, now) == "yellow"


def test_format_age():
    assert format_age(10) == "just now"
    assert format_age(120) == "2m"
    assert format_age(840) == "14m"
    assert format_age(7200) == "1h+"


from state import build_view


def test_build_view_empty():
    title, rows = build_view([], 1000)
    assert title == "🚦"
    assert rows == []


def test_build_view_counts_and_sort():
    now = 100000
    sessions = [
        {"project": "api", "state": "green", "updated": now - 5},
        {"project": "docs", "state": "red", "updated": now - 60},
        {"project": "web", "state": "yellow", "updated": now - 120},
        {"project": "old", "state": "red", "updated": now - 7200},  # -> gray
    ]
    title, rows = build_view(sessions, now)
    assert title == "🟢1 🟡1 🔴1 💀1"
    assert rows[0].startswith("🟡") and "web" in rows[0]
    assert rows[1].startswith("🔴") and "docs" in rows[1]
    assert rows[2].startswith("🟢") and "api" in rows[2]
    assert rows[3].startswith("💀") and "old" in rows[3]
    assert rows[0] == "🟡  web — needs you (2m)"


def test_build_view_tiebreak_recent_first():
    now = 100000
    sessions = [
        {"project": "older", "state": "green", "updated": now - 300},
        {"project": "newer", "state": "green", "updated": now - 10},
    ]
    _, rows = build_view(sessions, now)
    assert "newer" in rows[0]
    assert "older" in rows[1]
