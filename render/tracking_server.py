"""WebSocket VMC tracking server — receives MotionCaptureData from VMC protocol."""
import asyncio
import json
import logging
import struct
import threading
from dataclasses import dataclass, field

_log = logging.getLogger("karin.tracking")

VMC_PORT = 18081
VMC_MAGIC = 0x564d4301


@dataclass
class TrackingState:
    model_request: str = ""
    bone_transforms: dict = field(default_factory=dict)
    blend_shape_weights: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def consume_model_request(self) -> str:
        with self._lock:
            req = self.model_request
            self.model_request = ""
            return req

    def set_bone_transform(self, name: str, pos: tuple, rot: tuple) -> None:
        with self._lock:
            self.bone_transforms[name] = (pos, rot)

    def set_blend_shape_weight(self, name: str, weight: float) -> None:
        with self._lock:
            self.blend_shape_weights[name] = weight

    def consume_bone_transforms(self, peek=False) -> dict:
        with self._lock:
            if peek:
                return dict(self.bone_transforms)
            data = dict(self.bone_transforms)
            self.bone_transforms.clear()
            return data

    def consume_blend_shape_weights(self, peek=False) -> dict:
        with self._lock:
            if peek:
                return dict(self.blend_shape_weights)
            data = dict(self.blend_shape_weights)
            self.blend_shape_weights.clear()
            return data


class TrackingServer:
    """WebSocket + raw UDP server for VMC tracking data."""

    def __init__(self, state: TrackingState, port: int = VMC_PORT):
        self._state = state
        self._port = port
        self._udp_server = None
        self._ws_server = None
        self._loop = None
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_serve())
        except Exception as exc:
            _log.debug("VMC server: %s", exc)

    async def _async_serve(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: VMCUDPHandler(self._state),
            local_addr=("0.0.0.0", self._port),
        )
        _log.info("VMC UDP server on port %d", self._port)
        await asyncio.Event().wait()
        transport.close()

    def stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)


class VMCUDPHandler(asyncio.DatagramProtocol):
    def __init__(self, state: TrackingState):
        self._state = state

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        try:
            if len(data) < 12:
                return
            magic = struct.unpack_from("<I", data, 0)[0]
            if magic != VMC_MAGIC:
                return
            offset = 8
            packet_type = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            payload = data[offset:]
            if packet_type == 0x0001:
                self._parse_bone_transforms(payload)
            elif packet_type == 0x0010:
                self._parse_blend_shapes(payload)
        except Exception:
            pass

    def _parse_bone_transforms(self, payload: bytes) -> None:
        offset = 0
        while offset + 25 <= len(payload):
            name_len = payload[offset]
            offset += 1
            if offset + name_len > len(payload):
                break
            name = payload[offset:offset + name_len].decode("utf-8", errors="replace")
            offset += name_len
            if offset + 28 > len(payload):
                break
            pos = struct.unpack_from("<fff", payload, offset)
            offset += 12
            rot = struct.unpack_from("<ffff", payload, offset)
            offset += 16
            self._state.set_bone_transform(name, pos, rot)

    def _parse_blend_shapes(self, payload: bytes) -> None:
        offset = 0
        while offset + 5 <= len(payload):
            name_len = payload[offset]
            offset += 1
            if offset + name_len > len(payload):
                break
            name = payload[offset:offset + name_len].decode("utf-8", errors="replace")
            offset += name_len
            if offset + 4 > len(payload):
                break
            weight = struct.unpack_from("<f", payload, offset)[0]
            offset += 4
            self._state.set_blend_shape_weight(name, weight)


