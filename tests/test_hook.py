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


def test_notification_does_not_overwrite_red(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "red"


def test_notification_overwrites_green(tmp_path):
    now = time.time()
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
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


# --- concurrent sub-agents share the parent session_id ---------------------
# Live capture (Claude Code 2.1.234) shows sub-agent Pre/PostToolUse hooks
# firing under the parent's session_id, tagged with agent_id + agent_type,
# interleaved with the main thread's own events.

def test_subagent_activity_does_not_clear_main_thread_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "permission_prompt"}, now, directory=tmp_path)
    handle({"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1", "agent_type": "general-purpose"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "yellow"


def test_main_thread_activity_clears_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "permission_prompt"}, now, directory=tmp_path)
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "green"


def test_subagent_clears_the_yellow_it_raised(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "worker_permission_prompt", "agent_id": "a1"},
           now, directory=tmp_path)
    handle({"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "green"


def test_subagent_worktree_cwd_does_not_rename_the_project(tmp_path):
    now = time.time()
    handle({"hook_event_name": "UserPromptSubmit", "session_id": "s1",
            "cwd": "/Users/x/Projects/Mashevot"}, now, directory=tmp_path)
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "agent_id": "a1",
            "cwd": "/Users/x/Projects/Mashevot/.claude/worktrees/agent-a1"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["project"] == "Mashevot"


# --- not every Notification means "needs you" ------------------------------

def test_idle_notification_does_not_paint_a_running_session_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "idle_prompt"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "green"


def test_agent_completed_notification_does_not_paint_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "agent_completed"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "green"


def test_permission_notification_is_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "permission_prompt"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "yellow"


# --- a finished sub-agent hands the row back to the main thread ------------

def test_subagent_stop_reverts_to_main_thread_state(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    handle({"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "green"
    handle({"hook_event_name": "SubagentStop", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "red"


def test_subagent_stop_does_not_clear_main_thread_yellow(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Notification", "session_id": "s1", "cwd": "/a/b",
            "notification_type": "permission_prompt"}, now, directory=tmp_path)
    handle({"hook_event_name": "SubagentStop", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "yellow"


def test_subagent_stop_keeps_the_project_name(tmp_path):
    now = time.time()
    handle({"hook_event_name": "UserPromptSubmit", "session_id": "s1",
            "cwd": "/Users/x/Projects/Mashevot"}, now, directory=tmp_path)
    handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
            "cwd": "/Users/x/Projects/Mashevot/.claude/worktrees/agent-a1"},
           now, directory=tmp_path)
    session = load_sessions(now, directory=tmp_path)[0]
    assert session["project"] == "Mashevot"
    assert session["state"] == "green"


def test_subagent_stop_does_not_resurrect_an_unknown_session(tmp_path):
    now = time.time()
    handle({"hook_event_name": "SubagentStop", "session_id": "s1", "cwd": "/a/b",
            "agent_id": "a1"}, now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path) == []
