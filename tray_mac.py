"""macOS backend: traffic-light counts as text in the menu bar (rumps)."""
import time

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


def run():
    Claudelight().run()
