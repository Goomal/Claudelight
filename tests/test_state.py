from state import event_to_state, display_state, format_age, stale_ids


def test_event_to_state_mapping():
    assert event_to_state("SessionStart") == "red"
    assert event_to_state("UserPromptSubmit") == "green"
    assert event_to_state("PreToolUse") == "green"
    assert event_to_state("PostToolUse") == "green"
    assert event_to_state("Notification") == "yellow"
    assert event_to_state("Stop") == "red"
    assert event_to_state("SessionEnd") == "delete"
    assert event_to_state("SubagentStop") == "revert"
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
    labels = [label for label, _ in rows]
    assert labels[0].startswith("🟡") and "web" in labels[0]
    assert labels[1].startswith("🔴") and "docs" in labels[1]
    assert labels[2].startswith("🟢") and "api" in labels[2]
    assert labels[3].startswith("💀") and "old" in labels[3]
    assert labels[0] == "🟡  web — needs you (2m)"
    assert rows[0][1] is sessions[2]  # the row carries its session


def test_build_view_tiebreak_recent_first():
    now = 100000
    sessions = [
        {"project": "older", "state": "green", "updated": now - 300},
        {"project": "newer", "state": "green", "updated": now - 10},
    ]
    _, rows = build_view(sessions, now)
    assert "newer" in rows[0][0]
    assert "older" in rows[1][0]


from state import dominant_state


def test_dominant_state_empty_is_none():
    assert dominant_state([], 1000) is None


def test_dominant_state_yellow_wins():
    now = 100000
    sessions = [
        {"state": "green", "updated": now - 5},
        {"state": "red", "updated": now - 5},
        {"state": "yellow", "updated": now - 5},
    ]
    assert dominant_state(sessions, now) == "yellow"


def test_dominant_state_urgency_order():
    now = 100000
    assert dominant_state([{"state": "red", "updated": now}], now) == "red"
    assert dominant_state(
        [{"state": "green", "updated": now}, {"state": "red", "updated": now}], now
    ) == "red"
    assert dominant_state([{"state": "green", "updated": now}], now) == "green"


def test_dominant_state_applies_gray_staleness():
    now = 100000
    # a lone stale red -> gray
    assert dominant_state([{"state": "red", "updated": now - 7200}], now) == "gray"
    # green outranks a grayed-out red
    sessions = [
        {"state": "red", "updated": now - 7200},
        {"state": "green", "updated": now - 5},
    ]
    assert dominant_state(sessions, now) == "green"


def test_stale_ids_picks_only_gray():
    now = 10000
    sessions = [
        {"session_id": "dead", "state": "red", "updated": now - 7200},
        {"session_id": "fresh_red", "state": "red", "updated": now - 60},
        {"session_id": "old_green", "state": "green", "updated": now - 7200},
        {"session_id": "old_yellow", "state": "yellow", "updated": now - 7200},
    ]
    assert stale_ids(sessions, now) == ["dead"]


def test_stale_ids_empty():
    assert stale_ids([], 10000) == []


def test_notification_state_depends_on_notification_type():
    assert event_to_state("Notification", "permission_prompt") == "yellow"
    assert event_to_state("Notification", "worker_permission_prompt") == "yellow"
    assert event_to_state("Notification", "agent_needs_input") == "yellow"
    assert event_to_state("Notification", "idle_prompt") is None
    assert event_to_state("Notification", "agent_completed") is None
    assert event_to_state("Notification", "auth_success") is None
    assert event_to_state("Notification", None) == "yellow"  # pre-2.1 payloads
