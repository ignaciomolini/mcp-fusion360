"""Request bridge for dispatching JSON-RPC calls to Fusion 360's main thread.

Uses adsk.core.CustomEvent to delegate execution to Fusion's main thread,
which is required because most adsk API calls must run on the main thread.
Each request is paired with a threading.Event for synchronous waiting.
Concurrent requests are queued and processed sequentially.
"""

import queue
import threading

import adsk.core

from errors import FusionAPIError, OPERATION_TIMEOUT


class _BridgeEventHandler(adsk.core.CustomEventHandler):
    """CustomEventHandler adapter for the RequestBridge.

    The new Fusion 360 app API requires the handler to be a CustomEventHandler
    subclass (not a plain function), and registerCustomEvent() takes only the
    event id — the handler is then assigned via the returned CustomEvent's
    .add() method. This adapter forwards notify() calls to the bridge.
    """

    def __init__(self, bridge):
        super().__init__()
        self._bridge = bridge

    def notify(self, eventArgs):
        """Called by Fusion on the main thread when the CustomEvent fires."""
        self._bridge._on_custom_event(eventArgs)


class RequestBridge:
    """Bridge between HTTP handler threads and Fusion 360's main thread.

    Registers a CustomEvent with Fusion. When a request arrives, it is
    enqueued with a threading.Event. The CustomEvent handler on the main
    thread dequeues and processes one request at a time (sequential dispatch).
    """

    def __init__(self, event_id="Fusion360MCP_Bridge"):
        """Initialize the bridge.

        Args:
            event_id: Identifier for the CustomEvent registered with Fusion.
        """
        self._event_id = event_id
        self._queue = queue.Queue()
        self._handler_registered = False
        self._app = None
        self._event = None
        self._event_handler = None

    def register(self, app, handlers):
        """Register the CustomEvent handler with the Fusion application.

        Must be called once during add-in startup, on the main thread.

        Args:
            app: The adsk.core.Application instance.
            handlers: Dict mapping method names to handler callables.
                     Each handler receives (params) and returns a result dict.
        """
        self._app = app
        self._handlers = handlers
        # New API: registerCustomEvent takes only the event id and returns
        # a CustomEvent object to which the handler is then attached.
        self._event = app.registerCustomEvent(self._event_id)
        if self._event is None:
            raise RuntimeError(
                "Failed to register CustomEvent '{}' (likely duplicate id)".format(
                    self._event_id
                )
            )
        self._event_handler = _BridgeEventHandler(self)
        self._event.add(self._event_handler)
        self._handler_registered = True

    def unregister(self):
        """Unregister the CustomEvent. Called during add-in unload."""
        if self._handler_registered and self._app:
            try:
                # Remove handler first to break the reference, then unregister.
                if self._event is not None and self._event_handler is not None:
                    try:
                        self._event.remove(self._event_handler)
                    except Exception:
                        pass
                self._app.unregisterCustomEvent(self._event_id)
            except Exception:
                pass
            self._handler_registered = False
            self._event = None
            self._event_handler = None

    def submit(self, method, params, timeout=30):
        """Submit a request to be processed on the main thread.

        Enqueues the request and fires a CustomEvent to wake the main thread.
        Blocks the calling (HTTP) thread until the result is ready or timeout.

        Args:
            method: JSON-RPC method name (e.g. 'get_active_design_parameters').
            params: Dict of parameters for the method.
            timeout: Seconds to wait for the main thread to respond.

        Returns:
            The result dict from the handler.

        Raises:
            FusionAPIError: If the handler raises an exception, or if
                the request times out (code -32003).
        """
        event = threading.Event()
        envelope = {
            "method": method,
            "params": params,
            "event": event,
            "result": None,
            "error": None,
            "received": False,
        }
        self._queue.put(envelope)

        # Signal the main thread that work is available
        if self._app:
            try:
                self._app.fireCustomEvent(self._event_id)
            except Exception as exc:
                raise FusionAPIError(-32000, "Failed to fire custom event: {}".format(str(exc)))

        # Block until the main thread processes or timeout
        event.wait(timeout=timeout)

        if not envelope["received"]:
            # Timeout: main thread did not process in time
            raise FusionAPIError(OPERATION_TIMEOUT, "Operation timed out")

        if envelope["error"] is not None:
            # Handler raised an error
            raise envelope["error"]

        return envelope["result"]

    def _on_custom_event(self, args):
        """CustomEvent handler — runs on Fusion's main thread.

        Processes ALL pending requests sequentially from the queue.
        """
        # Process all pending requests (drain the queue)
        while True:
            try:
                envelope = self._queue.get_nowait()
            except queue.Empty:
                break

            method = envelope["method"]
            handler = self._handlers.get(method)

            if handler is None:
                envelope["error"] = FusionAPIError(-32601, "Method not found: {}".format(method))
                envelope["received"] = True
                envelope["event"].set()
                continue

            try:
                result = handler(envelope["params"])
                envelope["result"] = result
            except FusionAPIError as exc:
                envelope["error"] = exc
            except Exception as exc:
                envelope["error"] = FusionAPIError(-32000, str(exc))

            envelope["received"] = True
            envelope["event"].set()