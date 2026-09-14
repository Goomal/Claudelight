from terminal import script


def test_iterm_script_targets_the_session_id():
    source = script({"program": "iTerm.app", "session": "w0t0p0:GUID-1", "tty": ""})
    assert 'id of s is "GUID-1"' in source
    assert "com.googlecode.iterm2" in source


def test_apple_terminal_script_targets_the_tty():
    source = script({"program": "Apple_Terminal", "session": "x", "tty": "/dev/ttys003"})
    assert 'tty of t is "/dev/ttys003"' in source
    assert 'tell application "Terminal"' in source


def test_unknown_or_missing_terminal_is_not_focusable():
    assert script(None) is None
    assert script({}) is None
    assert script({"program": "WarpTerminal", "session": "", "tty": "/dev/ttys003"}) is None


def test_unusable_identity_is_not_focusable():
    assert script({"program": "iTerm.app", "session": "", "tty": ""}) is None
    assert script({"program": "Apple_Terminal", "session": "", "tty": ""}) is None


def test_quotes_cannot_escape_into_the_script():
    assert script({"program": "iTerm.app", "session": 'a" \nactivate\n"'}) is None
