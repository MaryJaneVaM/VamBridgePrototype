# -----------------------------------------------------------------------------
# Virtamate Server Bridge (TCP ↔ WebSocket)
# WebSocket Helper Utilities Module
# Copyright (c) 2025 MaryJaneVaM
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: server/ws_helpers.py
# -----------------------------------------------------------------------------

"""
WebSocket helper utilities for the Virtamate Server Bridge.

This module provides:
- State tracking for connected WebSocket clients
- Broadcast helpers for sending messages to all browsers
- Forwarding helpers to route browser commands to TCP clients

Functions
---------
broadcast :
    Broadcast a JSON message to all connected WebSocket clients.

set_forward_callback :
    Register the callback used to forward browser messages to TCP.

forward_to_tcp :
    Forward a browser-originated message to the TCP layer.
"""

import json


# State -----------------------------------------------------------------------
ws_clients = set()  # Active WebSocket connections
ws_identities = {}  # Mapping: websocket -> identity info (id, name, version)


# Broadcast -------------------------------------------------------------------
async def broadcast(message: dict):
    """
    Send a JSON message to all connected WebSocket clients.

    Parameters
    ----------
    message : dict
        The JSON-serializable message to broadcast.
    """
    try:
        data = json.dumps(message, separators=(",", ":"))
    except Exception as e:
        print(f"[WS] Broadcast serialization error: {e}")
        return

    for ws in list(ws_clients):
        try:
            await ws.send(data)
        except Exception as e:
            print(f"[WS] Broadcast send error: {e}")
            ws_clients.discard(ws)


# Forward ---------------------------------------------------------------------
_forward_cb = None


def set_forward_callback(cb):
    """
    Register a callback to forward browser messages to TCP clients.

    Parameters
    ----------
    cb : coroutine function
        The coroutine that will forward messages to TCP.
    """
    global _forward_cb
    _forward_cb = cb


async def forward_to_tcp(obj: dict):
    """
    Forward a browser message to TCP clients.

    Parameters
    ----------
    obj : dict
        The parsed browser message.

    Notes
    -----
    The actual forwarding logic is provided by the callback registered
    via `set_forward_callback`.
    """
    if _forward_cb is None:
        print("[WS] No forward callback registered")
        return

    try:
        await _forward_cb(obj)
    except Exception as e:
        print(f"[WS] Forward error: {e}")
