"""Windows backend: colored system-tray icon + tooltip counts (pystray).

The Windows tray has no text title like the macOS menu bar, so the counts
live in the hover tooltip and the icon paints the single most-urgent state.
Right-click opens the per-session list plus Quit.
"""
import threading
import time
from pathlib import Path

import pystray
from PIL import Image

from state import EMOJI, build_view, dominant_state, stale_ids
from store import delete_state, load_sessions

ASSETS = Path(__file__).resolve().parent / "assets"
_ICON_CACHE = {}


def _icon_image(state):
    """Load (and cache) the tray PNG for a state; None -> neutral icon."""
    name = state or "neutral"
    if name not in _ICON_CACHE:
        _ICON_CACHE[name] = Image.open(ASSETS / f"{name}.png")
    return _ICON_CACHE[name]


def _snapshot(now):
    try:
        sessions = load_sessions(now)
    except Exception:
        sessions = []
    title, rows = build_view(sessions, now)
    return title, rows, dominant_state(sessions, now), stale_ids(sessions, now)


def _clear_stale(icon, stale):
    for session_id in stale:
        delete_state(session_id)
    _refresh(icon)


def _build_menu(rows, stale, icon):
    items = [pystray.MenuItem(label, None, enabled=False) for label, _ in rows]
    if items:
        items.append(pystray.Menu.SEPARATOR)
    if stale:
        items.append(pystray.MenuItem(f"Clear {EMOJI['gray']} ({len(stale)})",
                                      lambda: _clear_stale(icon, stale)))
    items.append(pystray.MenuItem("Quit", lambda: icon.stop()))
    return pystray.Menu(*items)


def _refresh(icon):
    now = time.time()
    title, rows, state, stale = _snapshot(now)
    icon.icon = _icon_image(state)
    icon.title = title
    icon.menu = _build_menu(rows, stale, icon)
    icon.update_menu()


def run():
    icon = pystray.Icon("claudelight", _icon_image(None), "🚦")

    def setup(ic):
        ic.visible = True

        def _loop():
            while ic.visible:
                _refresh(ic)
                time.sleep(1)

        threading.Thread(target=_loop, daemon=True).start()

    icon.run(setup=setup)
