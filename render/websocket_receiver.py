"""WebSocket receiver — accept commands from Stream Deck, Streamer.bot, etc.

Listens on a configurable port for JSON commands:
  {"command": "expression", "value": "happy"}
  {"command": "set_weight", "bone": "head", "x": 0, "y": 0, "z": 0, "w": 1}
  {"command": "toggle", "feature": "particles"}
  {"command": "execute", "action": "dance"}
"""
import json
import threading
import logging
import asyncio

_log = logging.getLogger("karin.websocket")

try:
    import websockets
    import websockets.server
    _HAS_WEBSOCKETS = True
except ImportError:
    _HAS_WEBSOCKETS = False
    _log.info("websockets library not installed — WebSocket receiver disabled (pip install websockets)")


class WebSocketReceiver:
    """Async WebSocket server that receives commands and dispatches to callbacks."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self._host = host
        self._port = port
        self._running = False
        self._thread = None
        self._server = None
        self._clients: set = set()
        self._callbacks: dict[str, callable] = {}
        self._loop = None

    def register_callback(self, command: str, callback: callable):
        """Register a callback for a command type."""
        self._callbacks[command] = callback
        _log.info("WebSocket: registered callback for '%s'", command)

    def start(self):
        if self._running:
            return
        if not _HAS_WEBSOCKETS:
            _log.warning("WebSocket: websockets library not installed")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()
        _log.info("WebSocket receiver started: ws://%s:%d", self._host, self._port)

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        _log.info("WebSocket receiver stopped")

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        async with websockets.serve(
            self._handler, self._host, self._port,
            ping_interval=20, ping_timeout=10
        ) as server:
            self._server = server
            while self._running:
                await asyncio.sleep(0.5)

    async def _handler(self, ws, path=None):
        self._clients.add(ws)
        _log.info("WebSocket: client connected (%d total)", len(self._clients))
        try:
            async for message in ws:
                if not self._running:
                    break
                await self._process_message(ws, message)
        except Exception as e:
            _log.debug("WebSocket client error: %s", e)
        finally:
            self._clients.discard(ws)
            _log.info("WebSocket: client disconnected (%d remaining)", len(self._clients))

    async def _process_message(self, ws, raw_message: str):
        try:
            msg = json.loads(raw_message)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "invalid JSON"}))
            return

        command = msg.get("command", "")
        if not command:
            await ws.send(json.dumps({"error": "missing 'command' field"}))
            return

        callback = self._callbacks.get(command)
        if callback:
            try:
                result = callback(msg)
                if asyncio.iscoroutine(result):
                    result = await result
                await ws.send(json.dumps({"ok": True, "result": result}))
            except Exception as e:
                await ws.send(json.dumps({"error": str(e)}))
        else:
            await ws.send(json.dumps({"error": f"unknown command: {command}"}))

    def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        if not self._clients:
            return
        data = json.dumps(message)
        for ws in list(self._clients):
            try:
                asyncio.run_coroutine_threadsafe(ws.send(data), self._loop)
            except Exception:
                self._clients.discard(ws)

    @property
    def running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)
