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

## Installation

```
1. Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate        # Linux/macOS
   venv\Scripts\Activate.ps1       # Windows PowerShell

2. Upgrade pip (recommended)
   python -m pip install --upgrade pip

3. Install dependencies
   pip install -r requirements.txt
```

---

## Usage

Start the server:

```
python app.py
```

The server will:

- Accept TCP connections from VaM plugins  
- Accept WebSocket connections from browsers  
- Forward browser commands to the matching plugin  
- Broadcast plugin messages to all browsers  

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

Browser rendering:

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
