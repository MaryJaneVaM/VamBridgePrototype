# -----------------------------------------------------------------------------
# Virtamate Server Bridge (TCP ↔ WebSocket)
# TCP Helper Utilities Module
# Copyright (c) 2025 MaryJaneVaM
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: VaMBridgeServer/tcp_helpers.py
# -----------------------------------------------------------------------------

"""
TCP helper utilities for the Virtamate Server Bridge.

This module provides:
- Acknowledgement helpers for TCP handshake
- Broadcast scheduling from TCP threads into the asyncio loop
- Controller normalization and forwarding helpers
- Command validation and normalization utilities

Functions
---------
send_ack :
    Send an acknowledgement frame to a TCP client.

set_broadcast_callback :
    Register the broadcast coroutine used by schedule_broadcast.

schedule_broadcast :
    Schedule a broadcast coroutine from a TCP thread.

normalize_controllers :
    Validate and normalize controller dictionaries.

send_set_controller :
    Send a normalized set_controller command to a TCP client.

extract_payload :
    Extract the relevant payload from a command object.

normalize_cmd :
    Normalize incoming command names based on payload type.
"""

import json
import asyncio
from datetime import datetime, timezone
from core import send_frame, now_iso


# Acknowledge -----------------------------------------------------------------
def send_ack(conn, core: dict):
    """
    Send an acknowledgement back to the TCP client.

    Parameters
    ----------
    conn : socket.socket
        The TCP socket to send the acknowledgement to.
    core : dict
        The parsed command dictionary from the client.

    Notes
    -----
    Used only for the simplified handshake protocol.
    """
    try:
        ack_payload = {
            "cmd": "acknowledge",
            "id": core.get("id", ""),
            "name": core.get("name", ""),
            "ack": core.get("cmd", "") or "ok",
            "ts": now_iso(),
        }
        wire_plain = json.dumps(ack_payload, separators=(",", ":")).encode("utf-8")
        send_frame(conn, wire_plain)
        print(f"[TCP] Sent acknowledge for cmd={core.get('cmd')}")
    except Exception as e:
        print(f"[TCP] Failed to send acknowledge: {e}")


# Broadcast scheduling ---------------------------------------------------------
_broadcast_cb = None


def set_broadcast_callback(cb):
    """
    Register the broadcast coroutine used by schedule_broadcast.

    Parameters
    ----------
    cb : coroutine function
        The coroutine that will broadcast messages to WebSocket clients.
    """
    global _broadcast_cb
    _broadcast_cb = cb


def schedule_broadcast(loop: asyncio.AbstractEventLoop, payload: dict):
    """
    Schedule a broadcast coroutine from a TCP thread.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The asyncio loop used for scheduling.
    payload : dict
        The message to broadcast.
    """
    if _broadcast_cb is None:
        return
    try:
        loop.call_soon_threadsafe(asyncio.create_task, _broadcast_cb(payload))
    except Exception as e:
        print(f"[TCP] Broadcast scheduling error: {e}")


# Controllers -----------------------------------------------------------------
def normalize_controllers(controllers: list) -> list:
    """
    Validate and normalize controller dictionaries.

    Parameters
    ----------
    controllers : list
        A list of controller dictionaries.

    Returns
    -------
    list
        A list of normalized controller dictionaries.
    """
    normalized = []
    for idx, c in enumerate(controllers or []):
        ctrl = dict(c)
        cid = ctrl.get("id")

        if not cid or (isinstance(cid, str) and cid.strip() == ""):
            print(f"[TCP] Invalid controller id at index {idx}: {cid}")
            continue

        ctrl["id"] = str(cid)

        rot = dict(ctrl.get("rotation") or {})
        if "w" not in rot or rot["w"] is None:
            rot["w"] = 1.0
        ctrl["rotation"] = rot

        normalized.append(ctrl)

    return normalized


def send_set_controller(conn, controllers: list):
    """
    Send a set_controller command with normalized controllers to the TCP client.

    Parameters
    ----------
    conn : socket.socket
        The TCP socket to send the command to.
    controllers : list
        A list of controller dictionaries.
    """
    if not controllers:
        return

    controllers = normalize_controllers(controllers)
    if not controllers:
        print("[TCP] No valid controllers to send")
        return

    payload = {
        "cmd": "set_controller",
        "data": controllers,
        "ts": now_iso(),
    }
    wire_plain = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    send_frame(conn, wire_plain)
    print(f"[TCP] Forwarded set_controller with {len(controllers)} updates")


# Validation -------------------------------------------------------------------
def extract_payload(obj: dict):
    """
    Extract the relevant payload from a command object.

    Parameters
    ----------
    obj : dict
        The parsed command dictionary.

    Returns
    -------
    Any
        The extracted payload or None.
    """
    if "data" in obj and obj["data"] is not None:
        return obj["data"]
    if "morphs" in obj and obj["morphs"] is not None:
        return obj["morphs"]
    if "controllers" in obj and obj["controllers"] is not None:
        return obj["controllers"]
    return None


def normalize_cmd(cmd: str, obj: dict, payload):
    """
    Normalize incoming command names based on payload type.

    Parameters
    ----------
    cmd : str
        The original command name.
    obj : dict
        The parsed command dictionary.
    payload : Any
        The extracted payload.

    Returns
    -------
    str
        The normalized command name.
    """
    if cmd and cmd.endswith("_result"):
        return cmd

    if payload is not None:
        if "morphs" in obj and cmd not in ("read_all_morphs", "read_all_morphs_result"):
            return "read_all_morphs"
        if "controllers" in obj and cmd not in (
            "read_all_controllers",
            "read_all_controllers_result",
        ):
            return "read_all_controllers"

    return cmd or ""
