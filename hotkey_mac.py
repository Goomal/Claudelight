"""System-wide hotkey (⌃⌥⌘J) via Carbon.

rumps only offers menu key equivalents, which need the app to be frontmost —
useless for a menu bar app you are trying to reach *from* another app.
RegisterEventHotKey is system-wide, asks for no Accessibility grant, and
swallows the chord so it never reaches whatever you were typing in.
"""
import ctypes
import ctypes.util

CHORD = "⌃⌥⌘J"
_KEY_J = 38  # kVK_ANSI_J
_CONTROL, _OPTION, _COMMAND = 0x1000, 0x0800, 0x0100  # Carbon modifier masks
_KEYBOARD_CLASS = 0x6B657962  # 'keyb'
_HOTKEY_PRESSED = 5
_SIGNATURE = 0x636C6874  # 'clht'

_alive = []  # ctypes objects the C side holds pointers to; must outlive install()


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_void_p)


def _carbon():
    path = ctypes.util.find_library("Carbon")
    if not path:
        return None
    lib = ctypes.CDLL(path)
    lib.GetApplicationEventTarget.restype = ctypes.c_void_p
    lib.InstallEventHandler.restype = ctypes.c_int32
    lib.InstallEventHandler.argtypes = [
        ctypes.c_void_p, _HANDLER, ctypes.c_ulong,
        ctypes.POINTER(_EventTypeSpec), ctypes.c_void_p, ctypes.c_void_p]
    lib.RegisterEventHotKey.restype = ctypes.c_int32
    lib.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
    return lib


def install(callback):
    """Bind CHORD to `callback` app-wide. True when macOS accepted it.

    A press is delivered on the main run loop, the same thread the menu
    callbacks run on, so `callback` must return quickly.
    """
    lib = _carbon()
    if lib is None:
        return False

    def fired(next_handler, event, user_data):
        try:
            callback()
        except Exception:
            pass  # a hotkey must never take the tray down
        return 0

    handler = _HANDLER(fired)
    spec = _EventTypeSpec(_KEYBOARD_CLASS, _HOTKEY_PRESSED)
    target = lib.GetApplicationEventTarget()
    if lib.InstallEventHandler(target, handler, 1, ctypes.byref(spec),
                               None, None) != 0:
        return False
    ref = ctypes.c_void_p()
    if lib.RegisterEventHotKey(_KEY_J, _CONTROL | _OPTION | _COMMAND,
                               _EventHotKeyID(_SIGNATURE, 1), target, 0,
                               ctypes.byref(ref)) != 0:
        return False  # another app already owns the chord
    _alive.extend([lib, handler, ref])
    return True
