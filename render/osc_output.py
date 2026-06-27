import struct
import socket
import logging
import threading
import time

_log = logging.getLogger("karin.osc")


def _osc_string(s):
    b = s.encode("utf-8") + b"\x00"
    pad = (4 - len(b) % 4) % 4
    return b + b"\x00" * pad


def _osc_float(f):
    return struct.pack(">f", f)


def _osc_int(i):
    return struct.pack(">i", i)


def _build_message(address, *args):
    parts = [_osc_string(address)]
    type_tags = ","
    for a in args:
        if isinstance(a, float):
            type_tags += "f"
        elif isinstance(a, int):
            type_tags += "i"
        elif isinstance(a, str):
            type_tags += "s"
        else:
            type_tags += "f"
            a = float(a)
    parts.append(_osc_string(type_tags))
    for a in args:
        if isinstance(a, float):
            parts.append(_osc_float(a))
        elif isinstance(a, int):
            parts.append(_osc_int(a))
        elif isinstance(a, str):
            parts.append(_osc_string(a))
    return b"".join(parts)


class OscSender:
    def __init__(self, address="127.0.0.1", port=9000):
        self._address = address
        self._port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)

    def send_message(self, address, *args):
        try:
            data = _build_message(address, *args)
            self._sock.sendto(data, (self._address, self._port))
        except Exception as exc:
            _log.warning("OSC send failed: %s", exc)

    def send_blend_shapes(self, weights):
        for name, weight in weights.items():
            self.send_message("/VMC/Ext/Blend/Val", name, float(weight))

    def send_bone_poses(self, bones):
        for name, (pos, rot) in bones.items():
            if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                self.send_message("/VMC/Ext/Bone/Pos", name,
                                  float(pos[0]), float(pos[1]), float(pos[2]),
                                  float(rot[0]), float(rot[1]), float(rot[2]), float(rot[3]) if len(rot) >= 4 else 0.0)

    def close(self):
        self._sock.close()


class OscOutput:
    def __init__(self, state, address="127.0.0.1", port=9000, rate=30):
        self._state = state
        self._sender = OscSender(address, port)
        self._rate = rate
        self._interval = 1.0 / rate if rate > 0 else 1.0 / 30.0
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        _log.info("OSC output started: %s:%d @ %d fps", self._sender._address, self._sender._port, self._rate)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        _log.info("OSC output stopped")

    @property
    def running(self):
        return self._running

    def update_address(self, address, port):
        self._sender._address = address
        self._sender._port = port

    def update_rate(self, rate):
        self._rate = rate
        self._interval = 1.0 / rate if rate > 0 else 1.0 / 30.0

    def _run(self):
        while self._running:
            try:
                bs = self._state.consume_blend_shape_weights(peek=True)
                if bs:
                    self._sender.send_blend_shapes(bs)
                bones = self._state.consume_bone_transforms(peek=True)
                if bones:
                    self._sender.send_bone_poses(bones)
            except Exception as exc:
                _log.warning("OSC output loop: %s", exc)
            time.sleep(self._interval)

    def close(self):
        self.stop()
        self._sender.close()
