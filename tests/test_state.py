from state import event_to_state


def test_event_to_state_mapping():
    assert event_to_state("SessionStart") == "green"
    assert event_to_state("UserPromptSubmit") == "green"
    assert event_to_state("PreToolUse") == "green"
    assert event_to_state("PostToolUse") == "green"
    assert event_to_state("Notification") == "yellow"
    assert event_to_state("Stop") == "red"
    assert event_to_state("SessionEnd") == "delete"
    assert event_to_state("PreCompact") is None
