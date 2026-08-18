# Claudelight 🚦

Menu bar / system tray traffic light for your Claude Code sessions. Runs on
**macOS** (menu bar) and **Windows** (system tray).

- 🟢 green — Claude is working
- 🟡 yellow — needs your attention (blocked / waiting)
- 🔴 red — finished its turn
- 💀 gray — finished and untouched for over an hour

## Reading it

**macOS.** The number beside each icon is **how many sessions are in that
state**. So `🟢2 🟡1 🔴3` means two sessions working, one waiting on you, three
finished. Only non-zero states appear, ordered green → yellow → red → gray.
With no active sessions the icon falls back to a plain `🚦`.

Click the icon to drop down the per-session list — each row shows the project,
its state, and how long since it last changed, sorted most-urgent first.

**Sub-agents.** A session's sub-agents share its session id and run alongside
the main thread, so one session is still one row. Their activity keeps the row
green, but it never clears a 🟡 raised by someone else — only the thread that
raised the prompt can lower it — and their worktree never renames the project.
Yellow is reserved for the notifications that really need you (permission
prompts, an agent asking for input); idle and "agent finished" pings do not
repaint a running session.

**Windows.** The tray has no room for text, so the icon paints the single
**most-urgent** state (yellow → red → green → gray, or a plain 🚦 when idle).
Hover for the full counts (`🟢2 🟡1 🔴3`) in the tooltip; right-click for the
per-session list and Quit.

## Install

Installs only the deps for your platform (rumps on macOS; pystray + Pillow on
Windows) via environment markers in `requirements.txt`.

```bash
# macOS
python3 -m pip install --user -r requirements.txt

# Windows
python -m pip install -r requirements.txt
```

> **macOS note:** Homebrew's Python is "externally managed" (PEP 668) and
> refuses the command above with `error: externally-managed-environment`. If you
> hit that, add `--break-system-packages`:
>
> ```bash
> python3 -m pip install --user --break-system-packages -r requirements.txt
> ```

## Wire the hooks

Add this to your Claude Code `settings.json` (merge into an existing `hooks`
block if you have one). On macOS that's `~/.claude/settings.json`; on Windows,
`%USERPROFILE%\.claude\settings.json`.

Replace the `python3 /ABS/PATH/hook.py` command with the right interpreter and
absolute path for your OS:

- **macOS:** `python3 /ABS/PATH/hook.py`
- **Windows:** `python C:\\ABS\\PATH\\hook.py` (double the backslashes — it's JSON)

```json
{
  "hooks": {
    "SessionStart":     [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "PreToolUse":       [{"matcher": "", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "PostToolUse":      [{"matcher": "", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "Notification":     [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "Stop":             [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "SubagentStop":     [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}],
    "SessionEnd":       [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/hook.py"}]}]
  }
}
```

## Run

```bash
# macOS
python3 app.py

# Windows
python app.py
```

Leave it running. New Claude sessions appear automatically. Sessions started
*before* the hooks were installed stay invisible until their next event.
