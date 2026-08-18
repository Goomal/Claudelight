#!/usr/bin/env python3
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import event_to_state
from store import write_state, delete_state, read_state


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
