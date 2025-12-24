# VaM Bridge – Build & Deployment Instructions

This repository contains the source code for the VaM Bridge plugin and its companion Python servers.  
The build process prepares everything needed for the plugin to run inside Virt‑A‑Mate.

---

## 1. Requirements

Before building, make sure the following are installed:

### .NET SDK (8.0 or newer)
Used only to run the MSBuild automation tasks.  
Download:  
https://dotnet.microsoft.com/en-us/download

### .NET Framework 3.5 Developer Pack
Required because the project targets `net35`.  
Download:  
https://dotnet.microsoft.com/en-us/download/dotnet-framework/net35-sp1

### Python 3.10
Required for the Python server components.  
Other versions are not supported by Mediapipe.  
Download:  
https://www.python.org/downloads/release/python-3100/

Check your Python version:

```powershell
python --version
```

---

## 2. Clone the repository

```powershell
git clone https://github.com/MaryJaneVaM/VamBridgePrototype.git
cd VamBridgePrototype
```

---

## 3. Set the VaM path

The build system needs to know where your VaM installation is located.

```powershell
$env:VAM_PATH = "C:\PathTo\VaM"
```

To make this permanent:

```powershell
setx VAM_PATH "C:\PathTo\VaM"
```

The build will place the plugin files into:

`<VaM>\Custom\Scripts\MaryJane\VaMBridgePrototype`

---

## 4. Build the project

From the repository root:

```powershell
dotnet build
```

During the build:

### C# source files  
All `.cs` and `.cslist` files are copied into your VaM plugin folder.  
VaM loads these scripts directly.

### Python servers  
Each Python server project automatically:

- creates a virtual environment (only if missing)
- installs dependencies from `requirements.txt`
- downloads Mediapipe models (only if missing)

No manual setup is required.

---

## 5. Troubleshooting

### VaM path not set

If the build stops with an error, verify:

```powershell
echo $env:VAM_PATH
```

### Python issues

If dependencies fail to install, ensure you are using **Python 3.10**.

### Resetting a Python environment

To force a clean reinstall:

```powershell
Remove-Item -Recurse -Force PoseDetectionServer\venv
Remove-Item -Recurse -Force VaMBridgeServer\venv
dotnet build
```

---

## 6. Starting the servers (PowerShell)

After building the project, each server has its own virtual environment and can be started manually.

---

### Start the Pose Detection Server

```powershell
cd PoseDetectionServer
& venvScriptsActivate.ps1
python app.py
```

The server runs on:

`http://127.0.0.1:5100`

---

### Start the VaM Bridge Server (TCP ↔ WebSocket)

```powershell
cd VaMBridgeServer
& venvScriptsActivate.ps1
python app.py
```

By default it listens on:

- TCP: `127.0.0.1:5101`  
- WebSocket: `ws://127.0.0.1:5102`

---

### Running both servers at once

Open two PowerShell windows.

Window 1: Pose Detection Server

```powershell
cd PoseDetectionServer
& venvScriptsActivate.ps1
python app.py
```

Window 2: VaM Bridge Server

```powershell
cd VaMBridgeServer
& venvScriptsActivate.ps1
python app.py
```

---

## 7. Using VaM Bridge inside Virt‑A‑Mate

Once both servers are running, you can load the VaM Bridge plugins inside Virt‑A‑Mate and interact with the web clients.

### Launch Virt‑A‑Mate

1. Start VaM.exe  
2. Load the Creator Default scene (recommended)

---

### Load the Camera plugin

1. Select the WindowCamera atom  
2. Open the Control tab  
3. Go to Plugins  
4. Click Add Plugin → Select File  
5. Navigate to:  
   `MaryJane → VaMBridgePrototype → VaMBridgeCamera → VaMBridgeCamera.cslist`

---

### Load the Person plugin

1. Select the Person atom  
2. Open the Plugins tab  
3. Click Add Plugin → Select File  
4. Navigate to:  
   `MaryJane → VaMBridgePrototype → VaMBridgePerson → VaMBridgePerson.cslist`

Important:  
The Person atom must be named exactly:

`Person`

The plugin will not function if the atom name is changed.

---

## 8. Web clients

You can open all debug clients in any modern browser.

### Camera debug client

Open:

`VaMBridgeWebClient/camera_debug_client/camera.html`

Example workflow:

- Select a camera preset (e.g., Front)  
- Send View  
- Screenshot  
- Read View  

---

### Person debug client

Open:

`VaMBridgeWebClient/person_debug_client/person.html`

Notes:

- Only favorite morphs are listed  
- The JSON payload is editable  

---

### Pose debug client

Open:

`VaMBridgeWebClient/pose_debug_client/pose.html`

Workflow:

- Load any image  
- Press any Mediapipe button (Pose, Hands, Holistic)  
- View results and overlays  

---

## 9. Recommended setup

VaM Bridge works best with:

- Dual‑monitor setups (VaM Desktop on one screen, web clients on the other) 

---

## Enjoy building and extending VaM Bridge!

## 10. Disclaimer

VaM Bridge and its companion servers are intended to run **exclusively on localhost**.  
They are not designed, tested, or secured for remote access, public networks, or internet‑facing deployment.

By using this software, you acknowledge and agree to the following:

- All components must be run locally on your own machine.
- You are solely responsible for how you use, configure, or modify the software.
- The author(s) provide this project “as is” without any warranties of any kind.
- No liability is accepted for data loss, system damage, security issues, or any other harm resulting from the use or misuse of this software.
- Use this project at your own risk.

If you do not agree with these terms, do not use the software.

