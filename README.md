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
