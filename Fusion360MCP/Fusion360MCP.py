"""Fusion 360 MCP Server — Add-in entry point.

Starts the HTTP JSON-RPC server and the request bridge
that delegates API calls to Fusion's main thread.

Loaded by Fusion 360 when the add-in is started.
"""

import os
import sys

# Ensure the add-in directory is on sys.path so we can import local modules.
# The new Electron-based Fusion 360 app does not add the script's directory
# to sys.path automatically (unlike the legacy app), so we do it explicitly.
_ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _ADDIN_DIR not in sys.path:
    sys.path.insert(0, _ADDIN_DIR)

import adsk.core

from server import start_server
from fusion_bridge import RequestBridge
from handlers import HANDLERS


# Module-level references for cleanup
_bridge = None
_server_info = None
_shutting_down = False


def run(context):
    """Entry point called by Fusion 360 when the add-in is started.

    Registers a CustomEvent bridge and starts the HTTP server
    in a background thread.

    Args:
        context: Fusion 360 add-in context (provided by the framework).
    """
    global _bridge, _server_info, _shutting_down
    _shutting_down = False

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Let Fusion know we are loading
        ui.messageBox("Fusion 360 MCP Server starting...")

        # Create the bridge and register with Fusion's CustomEvent system
        _bridge = RequestBridge(event_id="Fusion360MCP_Bridge")
        _bridge.register(app, HANDLERS)

        # Log callback: write to Fusion's Text Commands palette
        def log_callback(msg):
            try:
                app.log(msg)
            except Exception:
                pass

        # Start the HTTP server
        _server_info = start_server(_bridge, log_callback=log_callback)

        ui.messageBox(
            "Fusion 360 MCP Server listening on port {}".format(
                _server_info["port"]
            )
        )

    except Exception as exc:
        try:
            ui = adsk.core.Application.get().userInterface
            ui.messageBox(
                "Failed to start Fusion 360 MCP Server:\n{}".format(str(exc))
            )
        except Exception:
            pass
        raise


def stop(context):
    """Entry point called by Fusion 360 when the add-in is stopped.

    Shuts down the HTTP server and unregisters the bridge.
    """
    global _bridge, _server_info, _shutting_down
    _shutting_down = True

    try:
        if _server_info is not None:
            server = _server_info.get("server")
            if server:
                server.shutdown()
                server.server_close()
            _server_info = None

        if _bridge is not None:
            _bridge.unregister()
            _bridge = None

        app = adsk.core.Application.get()
        app.log("Fusion 360 MCP Server stopped")

    except Exception:
        pass


__all__ = ["run", "stop"]
