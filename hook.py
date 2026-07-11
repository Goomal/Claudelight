#!/usr/bin/env python3
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import event_to_state
from store import write_state, delete_state


def handle(payload, now, directory=None):
    session_id = payload.get("session_id")
    if not session_id:
        return
    state = event_to_state(payload.get("hook_event_name"))
    if state == "delete":
        delete_state(session_id, directory)
    elif state in ("green", "yellow", "red"):
        project = os.path.basename(payload.get("cwd", "").rstrip("/")) or "unknown"
        write_state(session_id, project, state, payload.get("hook_event_name"),
                    now, directory)
    # unhandled events are ignored


def main():
    try:
        payload = json.load(sys.stdin)
        handle(payload, time.time())
    except Exception:
        pass  # a monitoring hook must never block the session
    sys.exit(0)


if __name__ == "__main__":
    main()
