"""macOS backend: traffic-light counts as text in the menu bar (rumps)."""
import time

import rumps

from state import EMOJI, build_view, stale_ids
from store import delete_state, load_sessions
from terminal import focus, script


class Claudelight(rumps.App):
    def __init__(self):
        super().__init__("🚦", quit_button=None)
        self._stale = []
        self._timer = rumps.Timer(self.refresh, 1)
        self._timer.start()
        self.refresh(None)

    def clear_stale(self, _):
        for session_id in self._stale:
            delete_state(session_id)
        self.refresh(None)

    def refresh(self, _):
        now = time.time()
        try:
            sessions = load_sessions(now)
        except Exception:
            sessions = []
        title, rows = build_view(sessions, now)
        self._stale = stale_ids(sessions, now)
        self.title = title
        self.menu.clear()
        for label, session in rows:
            terminal = session.get("terminal")
            # A row is only clickable when we know how to raise its window;
            # rumps greys out an item with no callback, which is the honest look.
            callback = (lambda _, t=terminal: focus(t)) if script(terminal) else None
            self.menu.add(rumps.MenuItem(label, callback=callback))
        if rows:
            self.menu.add(rumps.separator)
        if self._stale:
            self.menu.add(rumps.MenuItem(
                f"Clear {EMOJI['gray']} ({len(self._stale)})",
                callback=self.clear_stale))
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))


def run():
    Claudelight().run()
