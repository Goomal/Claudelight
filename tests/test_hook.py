import time
from hook import handle
from store import load_sessions


def test_handle_writes_green_with_project_from_cwd(tmp_path):
    now = time.time()
    handle({"hook_event_name": "UserPromptSubmit", "session_id": "s1",
            "cwd": "/Users/x/Projects/Claudelight"}, now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert sessions[0]["state"] == "green"
    assert sessions[0]["project"] == "Claudelight"


def test_handle_notification_is_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "yellow"


def test_handle_session_end_deletes(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "SessionEnd", "session_id": "s1"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path) == []


def test_handle_ignores_unknown_event_and_missing_id(tmp_path):
    now = time.time()
    handle({"hook_event_name": "PreCompact", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "Stop", "cwd": "/a/b"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path) == []
