# Virtamate Server Bridge (TCP ↔ WebSocket)

A lightweight bridge that relays plain JSON messages between a VaM plugin (TCP client) and web browsers (WebSocket clients).  
Designed for rapid prototyping, debugging, and real‑time data streaming.  
Base64‑encoded images are forwarded directly to browsers without modification.

---

## Features

- **TCP server**  
  Receives length‑prefixed JSON frames from VaM plugins (no encryption, no HMAC).

- **WebSocket hub**  
  Broadcasts plugin messages to all connected browsers.

- **Bidirectional forwarding**  
  - Browser → TCP (targeted by `id` + `name`)  
  - TCP → Browser (broadcast)

- **Base64 image relay**  
  Data URIs are passed through unchanged for immediate browser rendering.

- **Minimal dependencies**  
  Only the `websockets` package is required.

---

## Requirements

```
# Networking
websockets==12.0

# Core utilities
# (asyncio, socket, json, etc. are built into Python)
```

---

## Handling Base64 Images

The server does not decode or transform images.  
Plugins can send base64‑encoded PNG/JPEG frames as data URIs:

```
TCP → Browser message
{
  "cmd": "image",
  "src": "data:image/png;base64,...."
}
```

Browser rendering example:

```
<img src="data:image/png;base64,{{base64_string}}" />
```

---

## Project Structure

```
server/
├── app.py            # Entrypoint: starts TCP + WebSocket hub
├── ws_hub.py         # WebSocket broadcast hub
├── ws_helpers.py     # WebSocket utility helpers
├── tcp_helpers.py    # TCP receive/send helpers for VaM plugins
├── core.py           # Shared routing + message handling logic
└── requirements.txt  # Dependencies
```

---

