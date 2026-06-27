"""Spout output — share rendered texture with OBS/TouchDesigner via Spout2."""
import ctypes
import ctypes.wintypes as wintypes
import os
import logging
import numpy as np

_log = logging.getLogger(__name__)

_SPOUT_DLL = None
_SPOUT_LIB = None


def _load_spout():
    global _SPOUT_DLL, _SPOUT_LIB
    if _SPOUT_DLL is not None:
        return _SPOUT_DLL is not None

    dll_names = ["SpoutLibrary.dll", "Spout.dll"]
    search_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "..", "lib"),
        os.path.dirname(__file__),
        os.getcwd(),
    ]
    for d in search_dirs:
        for name in dll_names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    _SPOUT_DLL = ctypes.CDLL(path)
                    _log.info("Loaded Spout: %s", path)
                    return True
                except Exception:
                    pass

    for name in dll_names:
        try:
            _SPOUT_DLL = ctypes.CDLL(name)
            _log.info("Loaded Spout: %s", name)
            return True
        except Exception:
            pass

    _log.warning("Spout DLL not found — Spout output disabled")
    return False


class SpoutSender:
    """Thin wrapper around SpoutLibrary.dll for sending textures."""

    def __init__(self, name="KarinVTuber", width=1280, height=720):
        self._name = name
        self._width = width
        self._height = height
        self._handle = None
        self._active = False

        if not _load_spout():
            return

        try:
            dll = _SPOUT_DLL

            dll.spoutCreateSender.restype = ctypes.c_void_p
            dll.spoutCreateSender.argtypes = [
                ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            self._handle = dll.spoutCreateSender(
                name.encode("utf-8"), width, height, 0)
            if self._handle:
                self._active = True
                _log.info("Spout sender created: %s (%dx%d)", name, width, height)
            else:
                _log.warning("SpoutCreateSender returned null")
        except Exception as e:
            _log.warning("Spout init failed: %s", e)

    def send_image(self, rgba_data: bytes, width: int, height: int):
        """Send raw RGBA pixel data via Spout."""
        if not self._active or not self._handle:
            return False
        try:
            dll = _SPOUT_DLL
            dll.spoutSendImage.restype = ctypes.c_bool
            dll.spoutSendImage.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            buf = ctypes.create_string_buffer(rgba_data, len(rgba_data))
            # GL_RGBA = 0x1908, GL_UNSIGNED_BYTE = 0x1401
            result = dll.spoutSendImage(
                self._handle, buf, width, height, 0x1908, 0x1401)
            return result
        except Exception as e:
            _log.debug("Spout send failed: %s", e)
            return False

    def update_size(self, width: int, height: int):
        """Update sender dimensions if window resized."""
        if width == self._width and height == self._height:
            return
        self._width = width
        self._height = height
        if self._active and self._handle:
            try:
                dll = _SPOUT_DLL
                dll.spoutUpdateSender.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
                dll.spoutUpdateSender(self._handle, width, height)
            except Exception:
                pass

    def release(self):
        """Release the Spout sender."""
        if self._handle:
            try:
                dll = _SPOUT_DLL
                dll.spoutReleaseSender.argtypes = [ctypes.c_void_p]
                dll.spoutReleaseSender(self._handle)
            except Exception:
                pass
            self._handle = None
            self._active = False

    @property
    def active(self):
        return self._active
