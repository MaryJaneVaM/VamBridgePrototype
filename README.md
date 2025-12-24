# VaM Bridge – Build & Deployment Instructions

This repository contains the source code for the VaM Bridge plugin and its companion Python servers.  
The build process prepares everything needed for the plugin to run inside Virt‑A‑Mate.

---

## 1. Requirements

Before building, make sure the following are installed:

### ✔ .NET SDK (8.0 or newer)
Used only to run the MSBuild automation tasks.

### ✔ .NET Framework 3.5 Developer Pack
Required because the project targets `net35`.

### ✔ Python 3.10
Required for the Python server components.  
Other versions are not supported by Mediapipe.

Check your Python version:

```powershell
python --version
```

---

## 2. Clone the Repository

```powershell
git clone https://github.com/MaryJaneVaM/VamBridgePrototype.git
cd VamBridgePrototype
```

---

## 3. Set the VaM Path

The build system needs to know where your VaM installation is located.

```powershell
$env:VAM_PATH = "C:\Path\To\VaM"
```

To make this permanent:

```powershell
setx VAM_PATH "C:\Path\To\VaM"
```

The build will place the plugin files into:

```
<VaM>\Custom\Scripts\MaryJane\VaMBridgePrototype\
```

---

## 4. Build the Project

From the repository root:

```powershell
dotnet build
```

During the build:

### ✔ C# source files  
All `.cs` and `.cslist` files are copied into your VaM plugin folder.  
VaM loads these scripts directly.

### ✔ Python servers  
Each Python server project automatically:

- creates a virtual environment (only if missing)
- installs dependencies from `requirements.txt` (only if needed)
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
rmdir /s /q venv
dotnet build
```

---

Enjoy building and extending VaM Bridge!
