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
