#!/usr/bin/env python3
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import event_to_state
from store import write_state, delete_state, read_state

TASK_STARTED = re.compile(r"^Command running in background with ID: (\w+)\.")
AGENT_STARTED = re.compile(
    r"^Async agent launched successfully\..*?\bagentId: (\w+)", re.S)
TASK_DONE = re.compile(r"<task-id>(\w+)</task-id>")


def _tool_result_texts(item):
    content = item.get("content")
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                yield part["text"]


def _scan_entry(entry, started, ended):
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_result":
            for text in _tool_result_texts(item):
                match = TASK_STARTED.match(text) or AGENT_STARTED.match(text)
                if match:
                    started.add(match.group(1))
        elif item.get("type") == "tool_use" and item.get("name") == "TaskStop":
            task_id = (item.get("input") or {}).get("task_id")
            if task_id:
                ended.add(task_id)


def has_pending_task(transcript_path):
    """True when a background task was launched but has not ended.

    Background Bash commands and async sub-agents fire no hooks while they
    run, so at Stop time the transcript is the only record: a launch leaves
    "Command running in background with ID: x" (Bash) or "Async agent launched
    successfully. ... agentId: x" (Agent) in a tool result, completion injects
    a <task-id>x</task-id> notification, and a kill is a TaskStop tool call.
    """
    if not transcript_path:
        return False
    started, ended = set(), set()
    try:
        with open(transcript_path) as f:
            for line in f:
                if "task-id>" in line:
                    ended.update(TASK_DONE.findall(line))
                if "Command running in background" in line \
                        or "Async agent launched" in line or "TaskStop" in line:
                    try:
                        _scan_entry(json.loads(line), started, ended)
                    except ValueError:
                        continue
    except OSError:
        return False
    return bool(started - ended)


def project_name(payload, current, agent_id):
    """Sub-agents run in their own worktree, so their cwd is not the project."""
    if agent_id and current and current.get("project"):
        return current["project"]
    return os.path.basename(payload.get("cwd", "").rstrip("/")) or "unknown"


def handle(payload, now, directory=None):
    session_id = payload.get("session_id")
    if not session_id:
        return
    state = event_to_state(payload.get("hook_event_name"),
                           payload.get("notification_type"))
    if state == "delete":
        delete_state(session_id, directory)
        return
    if state not in ("green", "yellow", "red", "revert"):
        return  # unhandled events are ignored
    if payload.get("hook_event_name") == "Stop" \
            and has_pending_task(payload.get("transcript_path")):
        state = "green"  # turn ended, but a background task still runs and
        # its completion will re-invoke the session — that's working, not done

    # Sub-agents share the parent's session_id and run concurrently with it,
    # so an event's agent_id says which thread it came from (None = main).
    agent_id = payload.get("agent_id")  # thread that fired the event
    origin = agent_id  # thread the written state belongs to
    current = read_state(session_id, directory)
    if state == "revert":
        # A sub-agent finished; whatever it painted was only ever on loan.
        if not current or not current.get("main_state"):
            return
        if current.get("state") == "yellow" and current.get("origin") != agent_id:
            return  # another thread is still blocked on the user
        state, origin = current["main_state"], None
    if state == "yellow":
        if current and current.get("state") == "red":
            return  # idle notification after a finished turn — stay red
    elif state == "green" and current and current.get("state") == "yellow":
        if origin and origin != current.get("origin"):
            return  # a sub-agent's churn can't answer someone else's prompt

    main_state = (current or {}).get("main_state") if origin else state
    write_state(session_id, project_name(payload, current, agent_id), state,
                payload.get("hook_event_name"), now, directory, origin=origin,
                main_state=main_state)


def main():
    try:
        payload = json.load(sys.stdin)
        handle(payload, time.time())
    except Exception:
        pass  # a monitoring hook must never block the session
    sys.exit(0)


if __name__ == "__main__":
    main()
