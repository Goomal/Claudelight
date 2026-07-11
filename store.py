import json
import os
from pathlib import Path

STALE_DELETE = 86400  # delete files untouched for 24h


def state_dir():
    override = os.environ.get("CLAUDELIGHT_DIR")
    path = Path(override) if override else Path.home() / ".claude" / "trafficlight"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_state(session_id, project, state, reason, now, directory=None):
    directory = Path(directory) if directory else state_dir()
    final = directory / f"{session_id}.json"
    tmp = directory / f".{session_id}.json.tmp"
    data = {
        "session_id": session_id,
        "project": project,
        "state": state,
        "reason": reason,
        "updated": int(now),
    }
    tmp.write_text(json.dumps(data))
    os.replace(tmp, final)  # atomic rename


def delete_state(session_id, directory=None):
    directory = Path(directory) if directory else state_dir()
    try:
        (directory / f"{session_id}.json").unlink()
    except FileNotFoundError:
        pass


def load_sessions(now, directory=None, stale=STALE_DELETE):
    directory = Path(directory) if directory else state_dir()
    sessions = []
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            updated = int(data["updated"])
        except (ValueError, KeyError, OSError):
            continue  # skip half-written or corrupt files
        if now - updated > stale:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        sessions.append(data)
    return sessions
