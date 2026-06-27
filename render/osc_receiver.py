"""OSC Receiver for VTube Studio / MeowFace ARKit blendshapes."""
import logging
import socket
import struct
import threading
import time

_log = logging.getLogger("karin.osc_receiver")


class OscReceiver:
    """Receive ARKit blendshapes via OSC (VTube Studio / MeowFace protocol)."""

    _ARKIT_TO_VRM = {
        "eyeBlinkLeft": "blink_l",
        "eyeBlinkRight": "blink_r",
        "eyeLookDownLeft": "eye_down_l",
        "eyeLookDownRight": "eye_down_r",
        "eyeLookInLeft": "eye_in_l",
        "eyeLookInRight": "eye_in_r",
        "eyeLookOutLeft": "eye_out_l",
        "eyeLookOutRight": "eye_out_r",
        "eyeLookUpLeft": "eye_up_l",
        "eyeLookUpRight": "eye_up_r",
        "eyeSquintLeft": "blink_l",
        "eyeSquintRight": "blink_r",
        "eyeWideLeft": "eye_wide_l",
        "eyeWideRight": "eye_wide_r",
        "jawForward": "aa",
        "jawLeft": "aa",
        "jawRight": "aa",
        "jawOpen": "aa",
        "mouthClose": "mouth_close",
        "mouthFunnel": "ou",
        "mouthPucker": "ou",
        "mouthLeft": "aa",
        "mouthRight": "aa",
        "mouthSmileLeft": "fun",
        "mouthSmileRight": "fun",
        "mouthFrownLeft": "sorrow",
        "mouthFrownRight": "sorrow",
        "mouthDimpleLeft": "fun",
        "mouthDimpleRight": "fun",
        "mouthStretchLeft": "aa",
        "mouthStretchRight": "aa",
        "mouthRollLower": "aa",
        "mouthRollUpper": "aa",
        "mouthShrugLower": "aa",
        "mouthShrugUpper": "aa",
        "mouthPressLeft": "aa",
        "mouthPressRight": "aa",
        "mouthLowerDownLeft": "aa",
        "mouthLowerDownRight": "aa",
        "mouthUpperUpLeft": "aa",
        "mouthUpperUpRight": "aa",
        "browDownLeft": "angry",
        "browDownRight": "angry",
        "browInnerUp": "sorrow",
        "browOuterUpLeft": "sorrow",
        "browOuterUpRight": "sorrow",
        "cheekPuff": "fun",
        "cheekSquintLeft": "fun",
        "cheekSquintRight": "fun",
        "noseSneerLeft": "angry",
        "noseSneerRight": "angry",
        "tongueOut": "aa",
    }

    def __init__(self, port: int = 11111, bind_addr: str = "0.0.0.0"):
        self._port = port
        self._bind_addr = bind_addr
        self._sock = None
        self._thread = None
        self._running = False
        self._blendshape_weights = {}
        self._lock = threading.Lock()
        self._last_update = 0.0

    def start(self):
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self._bind_addr, self._port))
        self._sock.settimeout(0.1)
        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()
        _log.info("OscReceiver started on %s:%d", self._bind_addr, self._port)

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=1.0)
        _log.info("OscReceiver stopped")

    def _recv_loop(self):
        while self._running:
            try:
                data, addr = self._sock.recvfrom(65536)
                self._parse_osc(data)
            except socket.timeout:
                continue
            except Exception as e:
                _log.warning("OSC recv error: %s", e)

    def _parse_osc(self, data: bytes):
        """Parse OSC message - simplified for /VMC/Ext/Blend/Val or /VMC/Ext/Blend/Apply."""
        if len(data) < 4:
            return
        # Find OSC address
        addr_end = data.find(b"\x00")
        if addr_end == -1:
            return
        address = data[:addr_end].decode("utf-8", errors="ignore")
        if not address.startswith("/VMC/Ext/Blend"):
            return
        # Parse type tag
        type_start = (addr_end + 4) & ~3
        if type_start >= len(data):
            return
        type_tag = data[type_start:].split(b"\x00")[0].decode("ascii", errors="ignore")
        if not type_tag.startswith(","):
            return
        # Parse arguments
        arg_data = data[type_start + len(type_tag) + 1:]
        arg_data = arg_data[:len(arg_data) & ~3]  # pad
        offset = 0
        values = []
        for t in type_tag[1:]:
            if t == "f" and offset + 4 <= len(arg_data):
                values.append(struct.unpack(">f", arg_data[offset:offset + 4])[0])
                offset += 4
            elif t == "s" and offset < len(arg_data):
                end = arg_data.find(b"\x00", offset)
                if end != -1:
                    values.append(arg_data[offset:end].decode("utf-8", errors="ignore"))
                    offset = (end + 4) & ~3
        if not values:
            return
        # /VMC/Ext/Blend/Val name value
        # /VMC/Ext/Blend/Apply name value
        if len(values) >= 2 and isinstance(values[0], str):
            name = values[0]
            weight = float(values[1])
            self._set_blendshape(name, weight)
        # /VMC/Ext/Blend/Val (multiple values)
        elif len(values) >= 1 and all(isinstance(v, float) for v in values):
            # Bulk update - assumes standard ARKit order
            pass

    def _set_blendshape(self, arkit_name: str, weight: float):
        vrm_name = self._ARKIT_TO_VRM.get(arkit_name)
        if vrm_name is None:
            return
        with self._lock:
            self._blendshape_weights[vrm_name] = weight
            self._last_update = time.time()

    def consume_weights(self) -> dict[str, float]:
        """Get and clear pending blendshape weights."""
        with self._lock:
            weights = self._blendshape_weights.copy()
            self._blendshape_weights.clear()
            return weights

    def get_last_update(self) -> float:
        return self._last_update


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = OscReceiver(11111)
    r.start()
    try:
        while True:
            w = r.consume_weights()
            if w:
                print(w)
            time.sleep(0.016)
    except KeyboardInterrupt:
        r.stop()