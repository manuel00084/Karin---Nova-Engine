"""NDI output — share rendered texture via NDI (Network Device Interface).

Alternative to Spout for sharing rendered frames with OBS, TouchDesigner,
and other NDI-compatible applications over the network.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import logging
import numpy as np

_log = logging.getLogger(__name__)

_NDI_DLL = None
_NDI_FOUND = False


def _load_ndi():
    global _NDI_DLL, _NDI_FOUND
    if _NDI_DLL is not None:
        return _NDI_FOUND

    dll_names = ["Processing.NDI.Runtime.x64.dll", "ndi.dll"]
    search_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "lib"),
        os.path.dirname(__file__),
        os.getcwd(),
        "C:\\Program Files\\NDI\\SDK\\Bin\\x64",
        "C:\\Program Files (x86)\\NDI\\SDK\\Bin\\Win64",
    ]
    for d in search_dirs:
        for name in dll_names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    _NDI_DLL = ctypes.CDLL(path)
                    _log.info("Loaded NDI: %s", path)
                    _NDI_FOUND = True
                    return True
                except Exception:
                    pass

    for name in dll_names:
        try:
            _NDI_DLL = ctypes.CDLL(name)
            _log.info("Loaded NDI: %s", name)
            _NDI_FOUND = True
            return True
        except Exception:
            pass

    _log.info("NDI runtime not found — NDI output disabled (install NDI SDK)")
    return False


class NdiSender:
    """Thin wrapper around NDI runtime for sending RGBA textures."""

    def __init__(self, name: str = "Karin VTuber", width: int = 1280, height: int = 720):
        self._name = name
        self._width = width
        self._height = height
        self._sender = None
        self._frame = None
        self._active = False

        if not _load_ndi():
            return

        try:
            dll = _NDI_DLL
            dll.NDIlib_send_create.restype = ctypes.c_void_p
            dll.NDIlib_send_create.argtypes = [ctypes.c_void_p]
            dll.NDIlib_find_create_v2.restype = ctypes.c_void_p
            dll.NDIlib_find_create_v2.argtypes = [ctypes.c_void_p]
            dll.NDIlib_find_get_current_sources.restype = ctypes.POINTER(ctypes.c_void_p)
            dll.NDIlib_find_get_current_sources.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            dll.NDIlib_send_create.argtypes = [ctypes.c_void_p]

            find_desc = ctypes.create_string_buffer(256)
            find_handle = dll.NDIlib_find_create_v2(find_desc)
            if find_handle:
                import time
                time.sleep(0.5)
                sources = dll.NDIlib_find_get_current_sources(find_handle, 16)
                dll.NDIlib_find_destroy.argtypes = [ctypes.c_void_p]
                dll.NDIlib_find_destroy(find_handle)

            send_desc = ctypes.create_string_buffer(256)
            send_desc.raw = name.encode("utf-8")[:255]
            self._sender = dll.NDIlib_send_create(send_desc)
            if self._sender:
                self._active = True
                _log.info("NDI sender created: %s (%dx%d)", name, width, height)
            else:
                _log.warning("NDIlib_send_create returned null")
        except Exception as e:
            _log.warning("NDI init failed: %s", e)

    def send_image(self, rgba_data: bytes, width: int, height: int):
        """Send raw RGBA pixel data via NDI."""
        if not self._active or not self._sender:
            return False
        try:
            dll = _NDI_DLL
            frame_type = ctypes.c_int * 16
            frame = frame_type()
            frame[0] = width
            frame[1] = height
            buf = ctypes.create_string_buffer(rgba_data, len(rgba_data))
            frame_ptr = ctypes.cast(frame, ctypes.c_void_p)

            dll.NDIlib_send_send_video_v2.restype = ctypes.c_bool
            dll.NDIlib_send_send_video_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            result = dll.NDIlib_send_send_video_v2(self._sender, frame_ptr)
            return result
        except Exception as e:
            _log.debug("NDI send failed: %s", e)
            return False

    def update_size(self, width: int, height: int):
        if width == self._width and height == self._height:
            return
        self._width = width
        self._height = height

    def release(self):
        if self._sender:
            try:
                dll = _NDI_DLL
                dll.NDIlib_send_destroy.argtypes = [ctypes.c_void_p]
                dll.NDIlib_send_destroy(self._sender)
            except Exception:
                pass
            self._sender = None
            self._active = False

    @property
    def active(self) -> bool:
        return self._active
