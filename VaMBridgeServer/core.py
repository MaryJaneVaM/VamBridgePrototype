# -----------------------------------------------------------------------------
# Virtamate Server Bridge (TCP ↔ WebSocket)
# Core Utilities Module
# Copyright (c) 2025 MaryJaneVaM
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: VaMBridgeServer/core.py
# -----------------------------------------------------------------------------

"""
Core utilities for the Virtamate Server Bridge.

This module provides:
- Host/port configuration for TCP and WebSocket servers
- TCP framing helpers (length‑prefixed JSON frames)

Functions
---------
send_frame :
    Send a length‑prefixed JSON frame over TCP.

recv_exact :
    Read an exact number of bytes from a TCP socket.

recv_frame :
    Receive a full length‑prefixed frame from a TCP socket.
"""

import socket
import struct


# Configuration ---------------------------------------------------------------
HOST_TCP = "127.0.0.1"
PORT_TCP = 5101

HOST_WS = "127.0.0.1"
PORT_WS = 5102


# Framing helpers (TCP) -------------------------------------------------------
def send_frame(conn: socket.socket, payload_json: bytes) -> None:
    """
    Send a length-prefixed frame over TCP.

    Parameters
    ----------
    conn : socket.socket
        The TCP socket to send data through.
    payload_json : bytes
        The raw JSON payload to send.

    Notes
    -----
    Frame format:
        [4-byte little-endian length][payload]
    """
    length = len(payload_json)
    header = struct.pack("<I", length)
    conn.sendall(header + payload_json)


def recv_exact(conn: socket.socket, n: int) -> bytes:
    """
    Receive exactly `n` bytes from a TCP socket.

    Parameters
    ----------
    conn : socket.socket
        The TCP socket to read from.
    n : int
        Number of bytes to read.

    Returns
    -------
    bytes
        The received data.

    Raises
    ------
    ConnectionError
        If the socket closes before enough data is received.
    """
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed")
        buf.extend(chunk)
    return bytes(buf)


def recv_frame(conn: socket.socket) -> bytes:
    """
    Receive a length-prefixed frame from the socket.

    Parameters
    ----------
    conn : socket.socket
        The TCP socket to read from.

    Returns
    -------
    bytes
        The raw JSON payload.

    Notes
    -----
    Frame format:
        [4-byte little-endian length][payload]
    """
    header = recv_exact(conn, 4)
    length = struct.unpack("<I", header)[0]
    return recv_exact(conn, length)
