# Claudelight — Traffic Light for Claude Sessions

**Date:** 2026-07-11
**Status:** Approved design, ready for implementation plan

## Purpose

A macOS menu bar app that shows the live state of every open Claude Code
session as a traffic light, so the user knows at a glance which session needs
attention without constantly switching to each one.

- 🟢 green — Claude is working
- 🟡 yellow — needs attention (blocked / waiting on user)
- 🔴 red — finished its turn
- 💀 gray/skull — finished and left untouched for over an hour (stale)

## Architecture

Two decoupled parts communicating only through a shared folder. No server, no
ports, no direct process links.

```
Claude session ──hooks──► ~/.claude/trafficlight/<session_id>.json
                                     │
                       rumps app polls folder every 1s
                                     │
                       menu bar:  🟢2 🟡1 🔴1
                       dropdown:  per-session rows
```

- **Hook side** (`hook.py`): one script wired to 6 Claude Code hook events.
  Each firing writes/updates/deletes that session's JSON state file.
- **App side** (`app.py`): a rumps menu bar app that reads all state files
  every second and renders the menu bar title + dropdown.

The folder is the only interface. This makes each side independently testable
and restart-safe — state lives on disk, so restarting the app loses nothing.

## Components

### State file

One JSON file per session, named `<session_id>.json`, in
`~/.claude/trafficlight/`:

```json
{
  "session_id": "abc123",
  "project": "Claudelight",
  "state": "yellow",
  "reason": "Notification",
  "updated": 1752268800
}
```

- `session_id` — from the hook payload; also the filename.
- `project` — basename of the session `cwd`; used as the dropdown label.
- `state` — one of `green` | `yellow` | `red`. Gray is **computed by the app**,
  never written to disk.
- `reason` — the hook event name that produced this state (for debugging / row
  text).
- `updated` — unix seconds; drives gray-staleness detection and row age.

### `hook.py` — the hook script

A single script that every hook event routes to. It reads the hook JSON from
stdin (Claude Code provides at least `session_id`, `cwd`, `hook_event_name`),
maps the event to a color, and writes the state file. `SessionEnd` deletes the
file instead.

Event → state mapping:

| Hook event                                            | Action            |
|-------------------------------------------------------|-------------------|
| `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse` | state = green |
| `Notification`                                        | state = yellow    |
| `Stop`                                                | state = red       |
| `SessionEnd`                                          | delete state file |

Writes must be atomic (write to a temp file, then rename) so the polling app
never reads a half-written file.

The script is wired in `~/.claude/settings.json` under `hooks`, registering the
same script for all six events.

### `app.py` — the rumps menu bar app

- **Poll loop**: a rumps timer fires every 1 second. Each tick:
  1. Ensure the folder exists (create if missing).
  2. Read every `*.json` file. Skip any that fail to parse (half-written / bad).
  3. Delete any file whose `updated` is older than 24h (crashed session that
     never fired `SessionEnd`).
  4. Compute display state per session, including gray.
  5. Rebuild the menu bar title and dropdown.

- **Gray computation**: a session displays as gray when
  `state == "red" AND now - updated > 3600` (red, untouched for over an hour).

- **Menu bar title**: counts of nonzero colors, e.g. `🟢2 🟡1`. Only colors with
  at least one session are shown. Empty folder → a single dim `🚦`.

- **Dropdown rows**, sorted by urgency (yellow → red → green → gray):

  ```
  🟡  Claudelight — needs you (2m)
  🟢  api-server — working (just now)
  🔴  docs — done (14m)
  💀  old-thing — done (1h+)
  ──────────
  Quit
  ```

  Each row = colored dot + project name + state word + relative age. Rows are
  informational only in v1 (clicking does nothing). One `Quit` menu item.

## Data flow

1. User sends a prompt in a Claude session → `UserPromptSubmit` fires → `hook.py`
   writes `state: green`.
2. Claude runs tools → `PreToolUse` / `PostToolUse` keep it green (and refresh
   `updated`).
3. Claude asks for permission or goes idle waiting → `Notification` fires →
   `state: yellow`.
4. Claude finishes its turn → `Stop` fires → `state: red`.
5. An hour passes with no change → app renders that session as 💀 gray.
6. User closes the session → `SessionEnd` fires → file deleted → session drops
   out of the menu.

## Known limitations (accepted, not bugs)

- **Sessions already running before hooks are installed** never fired
  `SessionStart`, so they have no state file and stay invisible in the menu.
  They appear on their next event (next prompt or tool use writes green). This
  is accepted behavior for v1 — no code addresses it.

## Error handling

- **Corrupt / half-written files**: skipped during a tick; never crash the loop.
  Atomic writes on the hook side make this rare.
- **Missing folder**: app creates it on startup and each tick.
- **Crashed sessions** (no `SessionEnd`): files older than 24h are deleted by the
  app so dead sessions don't linger.
- **Hook script failures**: must exit 0 and never block the Claude session — a
  monitoring tool must not interfere with actual work. Any internal error is
  swallowed silently (best-effort telemetry).

## Testing

- **Pure functions** for the two core transforms, unit-tested with fixtures:
  - `event_name → state`
  - `list of state dicts + now → (menu title, sorted rows)` including gray logic.
- **Hook script**: feed sample stdin JSON payloads, assert the resulting file
  contents (and deletion on `SessionEnd`).
- **Manual smoke test**: drop a few fake JSON files into the folder, launch the
  app, confirm the menu bar title and dropdown match; age out one to gray.

## Scope (v1) / YAGNI

In scope: the four visible states, counts title, informational dropdown, atomic
hook writes, stale cleanup.

Explicitly out of scope for v1: clicking a row to focus/switch to a session,
notifications/sounds, packaging into a signed `.app`, config UI, per-project
custom colors. These can come later; none are needed to prove the core value.

## Files

```
Claudelight/
  app.py          # rumps menu bar app
  hook.py         # hook script, wired to all 6 events
  requirements.txt# rumps
  README.md       # install + hook wiring instructions
  tests/          # unit tests for pure functions + hook
```
