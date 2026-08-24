import json
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


# --- a Stop while a background task still runs is not "done" ----------------
# Background Bash commands fire no hooks while running, so the transcript is
# the only record: launch leaves "Command running in background with ID: x",
# completion injects a <task-id>x</task-id> notification, a kill is a TaskStop
# tool call. Entry shapes below mirror a live capture (Claude Code 2.1.241).

BG_START = {"type": "user", "message": {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "t1",
     "content": "Command running in background with ID: bmwp2jcqv. Output is "
                "being written to /tmp/tasks/bmwp2jcqv.output"}]}}
BG_DONE = {"type": "user", "message": {"role": "user", "content":
    "<task-notification>\n<task-id>bmwp2jcqv</task-id>\n"
    "<status>completed</status>\n</task-notification>"}}
BG_KILL = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "TaskStop", "input": {"task_id": "bmwp2jcqv"}}]}}
BG_PEEK = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "TaskOutput", "input": {"task_id": "bmwp2jcqv"}}]}}


def _transcript(tmp_path, entries):
    path = tmp_path / "transcript.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))
    return str(path)


def _stop(tmp_path, entries, now):
    handle({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/a/b",
            "transcript_path": _transcript(tmp_path, entries)},
           now, directory=tmp_path)
    return load_sessions(now, directory=tmp_path)[0]["state"]


def test_stop_with_running_background_task_stays_green(tmp_path):
    assert _stop(tmp_path, [BG_START, BG_PEEK], time.time()) == "green"


def test_stop_after_background_task_finished_is_red(tmp_path):
    assert _stop(tmp_path, [BG_START, BG_DONE], time.time()) == "red"


def test_stop_after_background_task_killed_is_red(tmp_path):
    assert _stop(tmp_path, [BG_START, BG_KILL], time.time()) == "red"


def test_stop_without_transcript_is_red(tmp_path):
    now = time.time()
    handle({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/a/b"},
           now, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path)[0]["state"] == "red"


# --- background sub-agents leave the same completion marker, but a different
# launch marker: "Async agent launched successfully. ... agentId: x". Entry
# shapes mirror a live capture (Claude Fable 5, 2026-08-24).

AGENT_START = {"type": "user", "message": {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "t2", "content": [
        {"type": "text",
         "text": "Async agent launched successfully. (This tool result is "
                 "internal metadata — never quote or paste any part of it.)\n"
                 "agentId: ab5e6bea66dbee1fc (internal ID - do not mention)\n"
                 "output_file: /tmp/tasks/ab5e6bea66dbee1fc.output"}]}]}}
AGENT_DONE = {"type": "user", "message": {"role": "user", "content":
    "<task-notification>\n<task-id>ab5e6bea66dbee1fc</task-id>\n"
    "<status>completed</status>\n</task-notification>"}}
AGENT_KILL = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "TaskStop",
     "input": {"task_id": "ab5e6bea66dbee1fc"}}]}}


def test_stop_with_running_background_agent_stays_green(tmp_path):
    assert _stop(tmp_path, [AGENT_START], time.time()) == "green"


def test_stop_after_background_agent_finished_is_red(tmp_path):
    assert _stop(tmp_path, [AGENT_START, AGENT_DONE], time.time()) == "red"


def test_stop_after_background_agent_killed_is_red(tmp_path):
    assert _stop(tmp_path, [AGENT_START, AGENT_KILL], time.time()) == "red"
