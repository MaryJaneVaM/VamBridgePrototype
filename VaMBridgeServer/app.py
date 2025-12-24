# -----------------------------------------------------------------------------
# Virtamate Server Bridge (TCP ↔ WebSocket)
# Copyright (c) 2025 MaryJaneVaM
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: VaMBridgeServer/app.py
# -----------------------------------------------------------------------------

"""
Unified TCP ↔ WebSocket bridge for Virtamate plugins and browser clients.

This module starts:
- A TCP server for VaM plugins (length‑prefixed JSON frames)
- A WebSocket server for browser clients
- A routing layer that forwards browser commands to the correct plugin
- A broadcast layer that sends plugin results to all browsers
"""

import asyncio
import threading
import socket
import json
import websockets

from core import HOST_TCP, PORT_TCP, HOST_WS, PORT_WS, send_frame, recv_frame

# Track connected clients and identities --------------------------------------
tcp_clients = set()
tcp_identities = {}  # mapping: conn -> {"id":..., "name":...}
ws_clients = set()
ws_identities = {}  # mapping: ws -> {"id":..., "name":...}


# TCP side (VaM plugins) -------------------------------------------------------
def handle_tcp_client(conn, addr, loop):
    """
    Handle a single TCP client connection from a VaM plugin.
    """
    print(f"[TCP] Connected: {addr}")
    tcp_clients.add(conn)

    try:
        while True:
            try:
                frame = recv_frame(conn)
                if not frame:
                    break
                obj = json.loads(frame.decode("utf-8"))
            except Exception as e:
                print(f"[TCP] Error from {addr}: {e}")
                break

            cmd = obj.get("cmd")

            # Handshake hello -------------------------------------------------
            if cmd == "hello":
                client_id = obj.get("id", "")
                client_name = obj.get("name", "")
                tcp_identities[conn] = {"id": client_id, "name": client_name}
                print(f"[TCP] Client identified: id={client_id}, name={client_name}")

                ack = {
                    "cmd": "acknowledge",
                    "ack": "hello",
                    "id": client_id,
                    "name": client_name,
                }
                send_frame(conn, json.dumps(ack).encode("utf-8"))
                asyncio.run_coroutine_threadsafe(broadcast(ack), loop)
                continue

            ident = tcp_identities.get(conn, {})
            print(
                f"[TCP] Received {cmd} from id={ident.get('id')} name={ident.get('name')}"
            )

            # Forward plugin results to browsers ------------------------------
            asyncio.run_coroutine_threadsafe(broadcast(obj), loop)

    finally:
        tcp_clients.discard(conn)
        tcp_identities.pop(conn, None)
        try:
            conn.close()
        except:
            pass
        print(f"[TCP] Closed: {addr}")


def tcp_server(loop):
    """
    Start the TCP server and accept incoming plugin connections.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST_TCP, PORT_TCP))
        s.listen()
        print(f"[TCP] Listening on {HOST_TCP}:{PORT_TCP}")

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_tcp_client, args=(conn, addr, loop), daemon=True
            ).start()


# WebSocket side (Browsers) ----------------------------------------------------
async def ws_handler(ws):
    """
    Handle a single WebSocket browser connection.
    """
    ws_clients.add(ws)
    print(f"[WS] Browser connected: {ws.remote_address}")

    try:
        async for msg in ws:
            try:
                obj = json.loads(msg)
            except Exception as e:
                print(f"[WS] Bad message: {e}")
                continue

            cmd = obj.get("cmd")

            # Browser handshake -----------------------------------------------
            if cmd == "hello":
                client_id = obj.get("id", "")
                client_name = obj.get("name", "")
                ws_identities[ws] = {"id": client_id, "name": client_name}
                print(f"[WS] Browser identified: id={client_id}, name={client_name}")

                ack = {
                    "cmd": "acknowledge",
                    "ack": "hello",
                    "id": client_id,
                    "name": client_name,
                }
                await ws.send(json.dumps(ack))
                continue

            # Forward browser commands to matching TCP clients ----------------
            target_id = obj.get("id")
            target_name = obj.get("name")
            wire = json.dumps(obj).encode("utf-8")

            for conn in list(tcp_clients):
                ident = tcp_identities.get(conn)
                if (
                    ident
                    and ident.get("id") == target_id
                    and ident.get("name") == target_name
                ):
                    try:
                        send_frame(conn, wire)
                        print(
                            f"[WS] Forwarded {cmd} to TCP id={target_id} name={target_name}"
                        )
                    except Exception as e:
                        print(f"[TCP] Send error: {e}")

    finally:
        ws_clients.discard(ws)
        ws_identities.pop(ws, None)
        print(f"[WS] Browser disconnected: {ws.remote_address}")


# Broadcast helper -------------------------------------------------------------
async def broadcast(message: dict):
    """
    Broadcast a JSON message to all connected WebSocket clients.
    """
    data = json.dumps(message)
    for ws in list(ws_clients):
        try:
            await ws.send(data)
        except Exception as e:
            print(f"[WS] Broadcast error: {e}")
            ws_clients.discard(ws)


# Entry point ------------------------------------------------------------------
async def start_async():
    """
    Start both TCP and WebSocket servers inside the asyncio event loop.
    """
    loop = asyncio.get_running_loop()
    threading.Thread(target=tcp_server, args=(loop,), daemon=True).start()

    try:
        async with websockets.serve(ws_handler, HOST_WS, PORT_WS):
            print(f"[WS] Listening on ws://{HOST_WS}:{PORT_WS}")
            print("\033[33mPress CTRL+C to quit\033[0m")
            await asyncio.Future()  # run forever

    except asyncio.CancelledError:
        print("Shutting down...")


def start():
    """Entry point wrapper for running the async server."""
    try:
        asyncio.run(start_async())
    except KeyboardInterrupt:
        print("Server stopped.")


if __name__ == "__main__":
    start()
