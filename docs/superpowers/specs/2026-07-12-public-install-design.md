# Claudelight — public install design

**Date:** 2026-07-12
**Goal:** Make Claudelight installable by any macOS Claude Code user via a public
GitHub repo, replacing the current manual pip + hand-edited `settings.json` flow
with a one-command installer.

## Scope

In scope:
- `install.sh` / `uninstall.sh` — self-contained, idempotent, safe.
- Safe merge of the 7 hooks into `~/.claude/settings.json`.
- Optional LaunchAgent for auto-start on login (opt-in).
- `LICENSE` (MIT), README rewrite, tests for the merge logic.
- Create GitHub repo under `Goomal` and push.

Out of scope (YAGNI): PyPI, Homebrew, Linux/Windows support. Claudelight is a
macOS menu bar app (`rumps`); "everyone" means every macOS Claude Code user.

## Install model

- Distribution: `git clone` then `./install.sh` (no curl-pipe-bash).
- `CLAUDELIGHT_HOME` = the directory `install.sh` runs from (the clone itself).
  No forced `~/.claudelight`; the clone location is the home.
- A virtualenv is created at `$CLAUDELIGHT_HOME/.venv` (already gitignored) with
  `rumps` installed into it. System / user site-packages are never touched.
- Hooks and the LaunchAgent both reference `$CLAUDELIGHT_HOME/.venv/bin/python3`
  and `$CLAUDELIGHT_HOME/hook.py` / `app.py` by absolute path.

## `install.sh`

Steps, in order:
1. **Platform guard.** If `uname` != `Darwin`, print a clear "macOS only"
   message and exit non-zero.
2. **Preflight (F2).** Verify `python3` exists and `python3 -m venv` works. If
   not (e.g. Command Line Tools absent), abort with a clear message telling the
   user to run `xcode-select --install`. Never proceed to mutate settings.json
   on a broken toolchain.
3. **Resolve home.** `CLAUDELIGHT_HOME` = absolute dir of the script.
4. **Python venv.** Create `$CLAUDELIGHT_HOME/.venv` if absent (`python3 -m
   venv` ships pip via ensurepip); `pip install` the pinned deps (`rumps`) into
   it.
5. **Merge hooks.** Back up `~/.claude/settings.json` to `settings.json.bak`,
   then merge our 7 hook entries idempotently (see Merge logic). Creates
   `settings.json` (and `~/.claude/`) if absent. **(F3)** If an existing
   `settings.json` is present but not valid JSON, abort without writing —
   report the file so the user can fix it; a partial write must never happen.
6. **LaunchAgent (opt-in, `--autostart`).** Write
   `~/Library/LaunchAgents/com.claudelight.plist` running the venv python on
   `app.py` at login. **(F1)** `KeepAlive` = `{"SuccessfulExit": false}` so a
   crash relaunches but a clean Quit (menu item) stays quit — otherwise launchd
   would make the app impossible to quit. **(F4)** Load with
   `launchctl bootstrap gui/$(id -u) <plist>`, falling back to
   `launchctl load -w <plist>` on older macOS. Without the flag, print the
   manual `.venv/bin/python3 app.py` run command instead.

Re-running `install.sh` is safe: venv reused, hooks not duplicated, plist
overwritten and reloaded.

## Merge logic (the risky part — unit tested)

Implemented as a pure function `merge_hooks(settings: dict, command: str) -> dict`
in a new module (`installer.py`), independent of file I/O so it is unit tested
directly.

- Our per-event entry uses the command string
  `"<venv-python> <CLAUDELIGHT_HOME>/hook.py"`. That full command string is the
  **marker**: an entry is "ours" iff its `command` contains
  `<CLAUDELIGHT_HOME>/hook.py`.
- For each of the 7 events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`,
  `PostToolUse`, `Notification`, `Stop`, `SessionEnd`):
  - `PreToolUse` / `PostToolUse` entries carry `"matcher": ""`; the others use
    the plain `{"hooks": [...]}` shape (matching the current README).
  - If an entry whose command contains the marker already exists for that event,
    leave it (idempotent). Otherwise append ours to that event's list.
- Existing unrelated hooks in any event are preserved untouched.
- The inverse `strip_hooks(settings, home) -> dict` removes only entries whose
  command contains `<home>/hook.py`, and drops any event key left empty.

## `uninstall.sh`

1. `launchctl bootout gui/$(id -u) <plist>` (fallback `launchctl unload`) and
   remove `com.claudelight.plist` if present.
2. Back up `settings.json`, run `strip_hooks`, write it back.
3. Leave the state dir (`~/.claude/trafficlight`) and the clone in place unless
   `--purge` is passed, which also removes the state dir and `.venv`.

## Repo additions

- `LICENSE` — MIT, author "Goomal".
- `install.sh`, `uninstall.sh`, `installer.py`.
- `tests/test_installer.py` — covers: merge into empty settings, merge preserving
  existing unrelated hooks, idempotent double-merge (no duplicates), correct
  `matcher` shape per event, `strip_hooks` removes only ours and cleans empties.
- README rewrite: one-liner clone+install, `--autostart` note, macOS-only
  callout, uninstall section, screenshot placeholder, keep the color legend.

## Publish

- `gh repo create Goomal/claudelight --public --source=. --remote=origin --push`.
- Confirm default branch `main`.

## Testing / verification

- `pytest` green (existing + new installer tests).
- Dry-run `install.sh` against a temp `HOME` to confirm settings merge and venv
  creation without touching the real environment.
- **(F5) Manual acceptance** (not unit-testable, needs a GUI session): fresh
  clone → `./install.sh --autostart` → open a Claude Code session → the traffic
  light appears in the menu bar and turns green on first prompt. LaunchAgent
  relaunch-on-crash and quit-stays-quit are verified by hand.
