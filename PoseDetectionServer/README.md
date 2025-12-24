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
- **Automatic crop‑based refinement**  
- Unified JSON schema with normalized and pixel coordinates  
- Uses MediaPipe `0.10.21`  
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

The server uses:

```
mediapipe==0.10.21
flask
flask-cors
opencv-python
numpy
```

Model files required:

- `pose_landmarker_heavy.task`
- `pose_landmarker_full.task` (optional)
- `hand_landmarker.task`

These are automatically handled by the build system.

---

## Endpoints

```
/detect/holistic
/detect/pose
/detect/hands
```

All endpoints accept raw image bytes (PNG/JPEG) and return a unified JSON structure.

---

## How detection works (high level)

1. Decode image bytes and smart‑resize  
2. Run full‑frame detection  
3. Compute bounding box  
4. If valid:  
   - crop  
   - upscale  
   - run second detection pass  
   - restore coordinates  
5. Otherwise: use full‑frame result  
6. Return unified JSON schema  

---

## Unified response schema

All endpoints return:

```
{
  "meta": { ... },
  "pose": { ... } | null,
  "hand_left": { ... } | null,
  "hand_right": { ... } | null
}
```

### `meta` block example

```
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
```

### Pose block example

```
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
```

### Hand block example

```
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
```

---

## Example requests and responses

### Holistic endpoint

```
POST /detect/holistic
```

Example response (simplified):

```
{
  "meta": { ... },
  "pose": { ... },
  "hand_left": { ... },
  "hand_right": { ... }
}
```

### Pose endpoint

```
POST /detect/pose
```

Example response:

```
{
  "meta": { ... },
  "pose": { ... },
  "hand_left": null,
  "hand_right": null
}
```

### Hands endpoint

```
POST /detect/hands
```

Example response:

```
{
  "meta": { ... },
  "pose": null,
  "hand_left": { ... },
  "hand_right": { ... }
}
```

---

## Project structure

```
pose_server/
  app.py
  routes/
  workers/
  utils/
  models/
  requirements.txt
  LICENSE
  NOTICE
```

---

## Notes

- The server is stateless and lightweight  
- The browser handles image capture + overlay drawing  
- The server handles detection + refinement  

---
