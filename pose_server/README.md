# Pose Detection Server  
### (MediaPipe Holistic + MediaPipe Tasks API v2)

This server receives full‑resolution images from a web client and performs **pose** and **hand** detection using:

- MediaPipe Holistic (legacy Solutions API)  
- MediaPipe Pose Landmarker (Tasks API v2)  
- MediaPipe Hand Landmarker (Tasks API v2)

Each detector is exposed through its own HTTP endpoint.  
The service is fully standalone so the main VaM server remains untouched.

---

## Features

- Multiple detection endpoints:  
  - `/detect/holistic` — full‑body + hands (Holistic API)  
  - `/detect/pose` — pose only (Tasks API v2)  
  - `/detect/hands` — hands only (Tasks API v2)
- Accepts raw PNG/JPEG image bytes  
- Internal downscaling using `smart_resize()`  
- **Automatic crop‑based refinement** (whenever a valid bounding box is available)  
- Unified JSON schema with normalized and pixel coordinates  
- Uses MediaPipe `0.10.21` (Tasks API + legacy API)  
- Lightweight Flask server  
- Easy to extend with new MediaPipe models  

---

## MediaPipe documentation

Holistic (Legacy API):  
https://developers.google.com/mediapipe/solutions/vision/holistic

Pose Landmarker (Tasks API v2):  
https://developers.google.com/mediapipe/solutions/vision/pose_landmarker

Hand Landmarker (Tasks API v2):  
https://developers.google.com/mediapipe/solutions/vision/hand_landmarker

MediaPipe Tasks Overview:  
https://developers.google.com/mediapipe/solutions/overview

Model Repository:  
https://developers.google.com/mediapipe/solutions/models

---

## Requirements

Python 3.10+ is supported and tested with:

mediapipe==0.10.21

Core dependencies:

flask  
flask-cors  
mediapipe==0.10.21  
opencv-python  
numpy  

---

## Model files (required)

Download the following `.task` models:

Pose Landmarker (Tasks API):  
- Heavy model:  
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task  
- Full model (optional alternative):  
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task  

Hand Landmarker (Tasks API):  
- Hand model:  
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task  

Place all downloaded models inside:

pose_server/models/

---

## Installation

### 1. Create and activate a Python virtual environment

Windows (PowerShell):

py -3.10 -m venv venv  
venv\Scripts\Activate.ps1  

### 2. Upgrade pip

python -m pip install --upgrade pip

### 3. Install dependencies

pip install -r requirements.txt

### 4. (Optional) Freeze exact versions

pip freeze > requirements.txt

---

## Usage

Start the server:

python app.py

Endpoints:

http://localhost:5005/detect/holistic  
http://localhost:5005/detect/pose  
http://localhost:5005/detect/hands  

---

## How detection works (high level)

For pose and hands, the pipeline is:

1. Decode image bytes and smart‑resize.  
2. Run **full‑frame** detection (pose / holistic / hands).  
3. Compute a **bounding box** (pose body bbox or hand bbox from wrist).  
4. If the bbox is valid:
   - Extract crop  
   - Upscale crop (e.g. to 512×512)  
   - Run a **second detection pass** on the crop  
   - Restore refined landmarks to **full‑image normalized coordinates**  
5. If refinement is not possible, fall back to the full‑frame detection.  
6. Return results in a **unified JSON schema**.

Crop‑based refinement is automatic whenever possible.

---

## Unified response schema

All endpoints return the same top‑level structure:

{
  "meta": { ... },
  "pose": { ... } | null,
  "hand_left": { ... } | null,
  "hand_right": { ... } | null
}

### `meta` block

{
  "source": "pose",
  "model": "pose_landmarker_heavy.task",
  "image": {
    "width": 1280,
    "height": 720,
    "aspect_ratio": 1.777
  },
  "resize_scale": 0.5,
  "frame_valid": true
}

### Pose block (`pose`)

{
  "landmarks": [
    {
      "id": 0,
      "name": "NOSE",
      "x_norm": 0.51,
      "y_norm": 0.16,
      "x_px": 652.0,
      "y_px": 115.0,
      "z": -0.64,
      "confidence": 0.99
    }
  ],
  "visibility_mask": [...],
  "completeness": 0.94,
  "bbox": { ... },
  "crop": { ... }
}

### Hand block (`hand_left`, `hand_right`)

{
  "handedness": "Left",
  "handedness_confidence": 0.92,
  "landmarks": [
    {
      "id": 0,
      "name": "WRIST",
      "x_norm": 0.66,
      "y_norm": 0.51,
      "x_px": 845.0,
      "y_px": 367.0,
      "z": 0.0,
      "confidence": 1.0
    }
  ],
  "completeness": 1.0,
  "crop": { ... }
}

---

## Example requests and responses

### 1. Holistic endpoint  
POST http://localhost:5005/detect/holistic

JavaScript example:

fetch("http://localhost:5005/detect/holistic", {
    method: "POST",
    body: resizedImageBlob
})
.then(r => r.json())
.then(data => console.log("Holistic result:", data));

Example response (simplified):

{
  "meta": { ... },
  "pose": { ... },
  "hand_left": { ... },
  "hand_right": { ... }
}

---

### 2. Pose Tasks API endpoint  
POST http://localhost:5005/detect/pose

JavaScript example:

fetch("http://localhost:5005/detect/pose", {
    method: "POST",
    body: resizedImageBlob
})
.then(r => r.json())
.then(data => console.log("Pose Tasks result:", data));

Example response (simplified):

{
  "meta": { ... },
  "pose": { ... },
  "hand_left": null,
  "hand_right": null
}

---

### 3. Hand Tasks API endpoint  
POST http://localhost:5005/detect/hands

JavaScript example:

fetch("http://localhost:5005/detect/hands", {
    method: "POST",
    body: resizedImageBlob
})
.then(r => r.json())
.then(data => console.log("Hand Tasks result:", data));

Example response (simplified):

{
  "meta": { ... },
  "pose": null,
  "hand_left": { ... },
  "hand_right": { ... }
}

---

## Project structure

pose_server/  
  app.py  
  routes/  
    holistic_route.py  
    pose_route.py  
    hand_route.py  
  workers/  
    holistic_worker.py  
    pose_worker.py  
    hand_worker.py  
  utils/  
    base_worker.py  
    bbox_utils.py  
    crop_utils.py  
    image_utils.py  
    landmark_utils.py  
    model_utils.py  
    schema_utils.py  
  models/  
    pose_landmarker_heavy.task  
    pose_landmarker_full.task  
    hand_landmarker.task  
  requirements.txt  
  LICENSE  
  NOTICE  

---

## Notes

- The server is stateless and lightweight.
- The browser handles:
  - receiving image blobs  
  - sending full‑resolution images  
  - drawing overlays (skeletons, hands)

- The pose server handles:
  - decoding image bytes  
  - internal downscaling  
  - automatic crop‑based refinement  
  - running pose/hand detection  
  - returning normalized and pixel keypoints  

### Future extensions

- Face detection  
- Gesture recognition  
- Iris tracking  
- Body segmentation  
- Face mesh  
- Object detection  

### API differences

- **Tasks API** — modern, fast, actively supported  
- **Holistic API** — legacy but still useful for combined body + hands
