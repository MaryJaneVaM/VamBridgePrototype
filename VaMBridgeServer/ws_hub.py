# -----------------------------------------------------------------------------
# Virtamate Server Bridge (TCP ↔ WebSocket)
# WebSocket Connection Handler Module
# Copyright (c) 2025 MaryJane
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: VaMBridgeServer/ws_hub.py
# -----------------------------------------------------------------------------

"""
WebSocket connection handler for the Virtamate Server Bridge.

This module manages:
- Browser WebSocket connections
- Handshake and identity registration
- Forwarding browser messages to TCP clients via ws_helpers

Functions
---------
ws_handler :
    Handle a single WebSocket browser connection.
"""

import json
from ws_helpers import ws_clients, ws_identities, forward_to_tcp


# WebSocket handler ------------------------------------------------------------
async def ws_handler(ws):
    """
    Handle a WebSocket client connection (browser).

    Parameters
    ----------
    ws : websockets.WebSocketServerProtocol
        The connected WebSocket client.

    Notes
    -----
    Messages are plain JSON with no encryption.
    """
    ws_clients.add(ws)
    print(f"[WS] Browser connected: {ws.remote_address}")

    try:
        async for msg in ws:
            try:
                obj = json.loads(msg)
            except Exception as e:
                print(f"[WS] Failed to parse message: {e}")
                continue

            cmd = obj.get("cmd")
            if not cmd:
                print("[WS] Ignored message without 'cmd'")
                continue

            # Browser identification ----------------------------------------
            if cmd == "hello":
                ws_identities[ws] = {
                    "id": obj.get("id", ""),
                    "name": obj.get("name", ""),
                    "version": obj.get("version", ""),
                }

                print(
                    f"[WS] Browser identified: "
                    f"id={ws_identities[ws]['id']} "
                    f"name={ws_identities[ws]['name']} "
                    f"version={ws_identities[ws]['version']} "
                    f"from {ws.remote_address}"
                )

                ack = {
                    "cmd": "acknowledge",
                    "ack": "hello",
                    "id": obj.get("id", ""),
                    "name": obj.get("name", ""),
                }

                try:
                    await ws.send(json.dumps(ack, separators=(",", ":")))
                except Exception as e:
                    print(f"[WS] Failed to send acknowledge: {e}")

                continue

            # Forward all other messages to TCP clients ---------------------
            try:
                await forward_to_tcp(obj)
            except Exception as e:
                print(f"[WS] Forward error: {e}")

    except Exception as e:
        print(f"[WS] Handler error: {e}")

    finally:
        ws_clients.discard(ws)
        ws_identities.pop(ws, None)
        print(f"[WS] Browser disconnected: {ws.remote_address}")
