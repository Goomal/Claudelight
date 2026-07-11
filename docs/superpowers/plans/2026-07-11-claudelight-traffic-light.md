# Claudelight Traffic Light Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A macOS menu bar app that shows the live state of every open Claude Code session as a traffic light (🟢 working / 🟡 needs you / 🔴 done / 💀 stale).

**Architecture:** Claude Code hooks write one JSON state file per session into `~/.claude/trafficlight/`. A rumps menu bar app polls that folder every second and renders a counts title plus a per-session dropdown. The folder is the only interface between the two sides; both are independently testable.

**Tech Stack:** Python 3, rumps (menu bar), pytest (tests). Standard library for everything else (json, os, pathlib).

## Global Constraints

- Target platform: macOS (rumps is macOS-only).
- Python 3.9+ (uses `pathlib`, f-strings, `os.replace`).
- State directory: `~/.claude/trafficlight/`, overridable via env var `CLAUDELIGHT_DIR` (used by tests).
- States written to disk: only `green` | `yellow` | `red`. `gray` is computed by the app at display time, never persisted.
- Gray rule: a `red` session becomes gray when `now - updated > 3600` seconds.
- Stale delete: state files untouched for more than 86400 seconds (24h) are deleted by the app.
- Emoji: green `🟢`, yellow `🟡`, red `🔴`, gray `💀`. Empty title: `🚦`.
- Hook script must never block a session: swallow all errors and `exit 0`.
- Atomic writes: write to a temp file then `os.replace` onto the final path.
- All modules live flat in the project root (`state.py`, `store.py`, `hook.py`, `app.py`); tests in `tests/`.

---

### Task 1: Project scaffold + state mapping

**Files:**
- Create: `requirements.txt`
- Create: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `EVENT_TO_STATE: dict[str, str]`
  - `event_to_state(event_name: str) -> str | None` — returns `"green"|"yellow"|"red"|"delete"|None`.
  - Module constants `GRAY_AFTER=3600`, `EMOJI`, `WORD`, `TITLE_ORDER`, `URGENCY` (used by later steps in this task).

- [ ] **Step 1: Initialize repo and dependency file**

```bash
cd /Users/shay/Documents/Claude/Projects/Claudelight
git init
printf 'rumps>=0.4.0\n' > requirements.txt
printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > .gitignore
```

- [ ] **Step 2: Write the failing test for `event_to_state`**

Create `tests/test_state.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/shay/Documents/Claude/Projects/Claudelight && python3 -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 4: Write `state.py` with constants and `event_to_state`**

Create `state.py`:

```python
EVENT_TO_STATE = {
    "SessionStart": "green",
    "UserPromptSubmit": "green",
    "PreToolUse": "green",
    "PostToolUse": "green",
    "Notification": "yellow",
    "Stop": "red",
    "SessionEnd": "delete",
}

GRAY_AFTER = 3600  # a red session older than this displays as gray

EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴", "gray": "💀"}
WORD = {"green": "working", "yellow": "needs you", "red": "done", "gray": "done"}
TITLE_ORDER = ["green", "yellow", "red", "gray"]  # menu bar count order
URGENCY = {"yellow": 0, "red": 1, "green": 2, "gray": 3}  # dropdown sort order


def event_to_state(event_name):
    """Map a hook event name to a state, 'delete', or None if unhandled."""
    return EVENT_TO_STATE.get(event_name)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore state.py tests/test_state.py
git commit -m "feat: scaffold project and hook event to state mapping"
```

---

### Task 2: Gray computation and age formatting

**Files:**
- Modify: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `GRAY_AFTER` from Task 1.
- Produces:
  - `display_state(session: dict, now: float) -> str` — session dict has keys `state` and `updated`; returns effective color including `"gray"`.
  - `format_age(seconds: float) -> str` — e.g. `"just now"`, `"2m"`, `"1h+"`.

- [ ] **Step 1: Add failing tests**

Append to `tests/test_state.py`:

```python
from state import display_state, format_age


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: FAIL with `ImportError: cannot import name 'display_state'`

- [ ] **Step 3: Implement `display_state` and `format_age`**

Append to `state.py`:

```python
def display_state(session, now):
    """Effective color for a session, applying the gray-staleness rule."""
    if session["state"] == "red" and now - session["updated"] > GRAY_AFTER:
        return "gray"
    return session["state"]


def format_age(seconds):
    """Human relative age from `now - updated` seconds."""
    if seconds < 45:
        return "just now"
    if seconds < 3600:
        return f"{round(seconds / 60)}m"
    return "1h+"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: gray staleness rule and relative age formatting"
```

---

### Task 3: Build the menu bar view

**Files:**
- Modify: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `display_state`, `format_age`, `EMOJI`, `WORD`, `TITLE_ORDER`, `URGENCY`.
- Produces:
  - `build_view(sessions: list[dict], now: float) -> tuple[str, list[str]]` — returns `(menu_bar_title, [row_string, ...])`. Each session dict has `project`, `state`, `updated`.

- [ ] **Step 1: Add failing tests**

Append to `tests/test_state.py`:

```python
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
    assert rows[0].startswith("🟡") and "web" in rows[0]
    assert rows[1].startswith("🔴") and "docs" in rows[1]
    assert rows[2].startswith("🟢") and "api" in rows[2]
    assert rows[3].startswith("💀") and "old" in rows[3]
    assert rows[0] == "🟡  web — needs you (2m)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_view'`

- [ ] **Step 3: Implement `build_view`**

Append to `state.py`:

```python
def build_view(sessions, now):
    """Pure transform: sessions -> (menu bar title, sorted row strings)."""
    display = [(display_state(s, now), s) for s in sessions]

    counts = {}
    for state, _ in display:
        counts[state] = counts.get(state, 0) + 1
    parts = [f"{EMOJI[c]}{counts[c]}" for c in TITLE_ORDER if counts.get(c)]
    title = " ".join(parts) if parts else "🚦"

    display.sort(key=lambda ds: (URGENCY[ds[0]], -ds[1]["updated"]))
    rows = [
        f"{EMOJI[state]}  {s['project']} — {WORD[state]} ({format_age(now - s['updated'])})"
        for state, s in display
    ]
    return title, rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: build menu bar title and sorted dropdown rows"
```

---

### Task 4: State file storage

**Files:**
- Create: `store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: nothing from other modules.
- Produces:
  - `state_dir() -> Path` — ensures and returns the state directory.
  - `write_state(session_id, project, state, reason, now, directory=None) -> None` — atomic write.
  - `delete_state(session_id, directory=None) -> None` — safe if missing.
  - `load_sessions(now, directory=None, stale=86400) -> list[dict]` — reads all files, skips unparseable, deletes stale.

- [ ] **Step 1: Write failing tests**

Create `tests/test_store.py`:

```python
import time
from store import write_state, delete_state, load_sessions


def test_write_and_load(tmp_path):
    now = time.time()
    write_state("s1", "proj", "green", "Stop", now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "s1"
    assert sessions[0]["project"] == "proj"
    assert sessions[0]["state"] == "green"
    assert sessions[0]["reason"] == "Stop"


def test_delete_is_safe_when_missing(tmp_path):
    now = time.time()
    write_state("s1", "proj", "green", "x", now, directory=tmp_path)
    delete_state("s1", directory=tmp_path)
    assert load_sessions(now, directory=tmp_path) == []
    delete_state("nope", directory=tmp_path)  # no error


def test_load_skips_bad_files(tmp_path):
    (tmp_path / "bad.json").write_text("{not json")
    now = time.time()
    write_state("good", "p", "green", "x", now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "good"


def test_load_deletes_stale(tmp_path):
    now = time.time()
    write_state("old", "p", "red", "x", now - 90000, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path, stale=86400) == []
    assert not (tmp_path / "old.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'store'`

- [ ] **Step 3: Implement `store.py`**

Create `store.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat: atomic state file storage with stale cleanup"
```

---

### Task 5: Hook script

**Files:**
- Create: `hook.py`
- Test: `tests/test_hook.py`

**Interfaces:**
- Consumes: `event_to_state` (Task 1), `write_state` / `delete_state` (Task 4).
- Produces:
  - `handle(payload: dict, now: float, directory=None) -> None` — maps a hook payload to a store write/delete.
  - `main()` — reads stdin JSON, calls `handle`, always exits 0.

- [ ] **Step 1: Write failing tests**

Create `tests/test_hook.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_hook.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hook'`

- [ ] **Step 3: Implement `hook.py`**

Create `hook.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_hook.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Verify the full suite still passes**

Run: `python3 -m pytest -v`
Expected: PASS (14 tests total)

- [ ] **Step 6: Commit**

```bash
git add hook.py tests/test_hook.py
git commit -m "feat: hook script mapping events to state files"
```

---

### Task 6: Menu bar app, docs, and manual smoke test

**Files:**
- Create: `app.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `load_sessions` (Task 4), `build_view` (Task 3).
- Produces: a runnable `python3 app.py` menu bar app. (rumps UI is verified manually, not unit-tested.)

- [ ] **Step 1: Implement `app.py`**

Create `app.py`:

```python
#!/usr/bin/env python3
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rumps
from state import build_view
from store import load_sessions


class Claudelight(rumps.App):
    def __init__(self):
        super().__init__("🚦", quit_button=None)
        self._timer = rumps.Timer(self.refresh, 1)
        self._timer.start()
        self.refresh(None)

    def refresh(self, _):
        now = time.time()
        try:
            sessions = load_sessions(now)
        except Exception:
            sessions = []
        title, rows = build_view(sessions, now)
        self.title = title
        self.menu.clear()
        for row in rows:
            self.menu.add(rumps.MenuItem(row))
        if rows:
            self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))


if __name__ == "__main__":
    Claudelight().run()
```

- [ ] **Step 2: Install the dependency**

Run: `cd /Users/shay/Documents/Claude/Projects/Claudelight && python3 -m pip install -r requirements.txt`
Expected: rumps installs successfully.

- [ ] **Step 3: Manual smoke test with fake state files**

Run these to seed three sessions (one that will show gray):

```bash
mkdir -p ~/.claude/trafficlight
NOW=$(date +%s)
printf '{"session_id":"a","project":"api","state":"green","reason":"PostToolUse","updated":%s}\n' "$NOW" > ~/.claude/trafficlight/a.json
printf '{"session_id":"b","project":"web","state":"yellow","reason":"Notification","updated":%s}\n' "$NOW" > ~/.claude/trafficlight/b.json
printf '{"session_id":"c","project":"old","state":"red","reason":"Stop","updated":%s}\n' "$((NOW-7200))" > ~/.claude/trafficlight/c.json
python3 app.py
```

Expected in the menu bar: `🟢1 🟡1 💀1`. Open the dropdown: `🟡 web — needs you`, then `🟢 api — working`, then `💀 old — done (1h+)`. Confirm, then quit via the Quit item. Clean up: `rm ~/.claude/trafficlight/*.json`.

- [ ] **Step 4: Write `README.md` with install and hook wiring**

Create `README.md`:

````markdown
# Claudelight 🚦

macOS menu bar traffic light for your Claude Code sessions.

- 🟢 green — Claude is working
- 🟡 yellow — needs your attention (blocked / waiting)
- 🔴 red — finished its turn
- 💀 gray — finished and untouched for over an hour

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Wire the hooks

Add this to `~/.claude/settings.json` (merge into an existing `hooks` block if
you have one). Replace `/ABS/PATH` with this repo's absolute path.

```json
{
  "hooks": {
    "SessionStart":     [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "PreToolUse":       [{"matcher": "", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "PostToolUse":      [{"matcher": "", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "Notification":     [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "Stop":             [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "SessionEnd":       [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}]
  }
}
```

## Run

```bash
python3 app.py
```

Leave it running. New Claude sessions appear automatically. Sessions started
*before* the hooks were installed stay invisible until their next event.
````

- [ ] **Step 5: Commit**

```bash
git add app.py README.md
git commit -m "feat: rumps menu bar app and setup docs"
```

---

## Notes for the implementer

- Run the whole suite anytime with `python3 -m pytest -v` from the project root (14 tests when complete).
- `app.py` and `hook.py` add their own directory to `sys.path` so they import `state`/`store` when run as scripts from anywhere.
- Do not add features beyond this plan (no click-to-focus, no sounds, no packaging) — those are explicitly out of v1 scope.
