#!/usr/bin/env python3
"""Claudelight tray app: dispatch to the per-platform backend.

Backends are imported lazily because their GUI deps are platform-specific
(rumps needs macOS Foundation; pystray/Pillow are the Windows path).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if sys.platform == "darwin":
        from tray_mac import run
    elif sys.platform == "win32":
        from tray_win import run
    else:
        sys.exit(f"Claudelight has no tray backend for platform {sys.platform!r} "
                 "(supported: macOS, Windows).")
    run()


if __name__ == "__main__":
    main()
