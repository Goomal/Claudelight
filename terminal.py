"""Which terminal window a session lives in, and how to raise it.

The hook records the identity (env vars plus the controlling tty, captured
once per session); the macOS tray turns it back into an AppleScript that
selects that window/tab and brings the app forward.
"""
import os
import re
import subprocess

SAFE = re.compile(r"^[A-Za-z0-9:/._-]+$")  # ids we are willing to inline

ITERM = """tell application id "com.googlecode.iterm2"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        if id of s is "{session}" then
          select w
          select t
          select s
          activate
          return
        end if
      end repeat
    end repeat
  end repeat
end tell"""

APPLE_TERMINAL = """tell application "Terminal"
  repeat with w in windows
    repeat with t in tabs of w
      if tty of t is "{tty}" then
        set selected of t to true
        set index of w to 1
        activate
        return
      end if
    end repeat
  end repeat
end tell"""


def _tty():
    """Controlling terminal of this process, or "" when it has none.

    The hook's own stdin is a pipe, so ps is the way to the tty it inherited.
    """
    try:
        out = subprocess.run(["ps", "-o", "tty=", "-p", str(os.getpid())],
                             capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    return f"/dev/{out}" if out and out != "??" else ""


def detect():
    """Identity of the terminal running this session, or None if not in one."""
    program = os.environ.get("TERM_PROGRAM")
    if not program:
        return None
    return {
        "program": program,
        "session": os.environ.get("ITERM_SESSION_ID", ""),  # "w0t0p0:<session id>"
        "tty": _tty(),
    }


def script(terminal):
    """AppleScript raising this terminal's window, or None if we can't target it.

    iTerm2 is matched on the session id it exports into the environment;
    Terminal.app has no such id, so its tabs are matched on tty instead.
    """
    program = (terminal or {}).get("program")
    if program == "iTerm.app":
        session = (terminal.get("session") or "").split(":")[-1]
        if SAFE.match(session):
            return ITERM.format(session=session)
    elif program == "Apple_Terminal":
        tty = terminal.get("tty") or ""
        if SAFE.match(tty):
            return APPLE_TERMINAL.format(tty=tty)
    return None


def most_urgent(rows):
    """Terminal of the first row we can actually raise, or None.

    build_view already sorts rows most-urgent first, so the first focusable
    one is the target; a session in an unscriptable terminal is skipped rather
    than swallowing the click.
    """
    for _, session in rows:
        terminal = session.get("terminal")
        if script(terminal):
            return terminal
    return None


def focus(terminal):
    """Bring the session's terminal window to the front. Best effort."""
    source = script(terminal)
    if not source:
        return
    try:
        subprocess.run(["osascript", "-e", source], check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass
