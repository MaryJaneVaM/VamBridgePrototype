# -----------------------------------------------------------------------------
# Pose Detection Server
# Copyright (c) 2025 MaryJaneVaM
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
# 4.0 International License (CC BY-NC-SA 4.0).
#
# You may share and adapt this file for non-commercial purposes, provided that
# you give appropriate credit and distribute your contributions under the same
# license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# Path: pose_server/utils/bbox_utils.py
# -----------------------------------------------------------------------------

"""
Shared bounding-box and cropping utilities for Pose and Hand workers.

This module provides helper functions for computing bounding boxes from pose
and hand landmarks, extracting and upscaling crops, enhancing lighting, and
restoring landmark coordinates back to full-image space.

Included utilities:
- compute_hand_bbox_from_wrist()
- compute_person_bbox_from_pose()
- compute_torso_bbox()
- compute_pose_bbox_px()        (pixel-space pose bbox)
- extract_crop()
- upscale_crop()
- enhance_lighting()
- restore_landmarks_to_full_image()

A DEBUG flag is available to save intermediate crops for inspection.
"""

import cv2
import numpy as np
import os

# Debugging flag to save debug crops
DEBUG = False

# Base directory = project root (pose_server/)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEBUG_DIR = os.path.join(_BASE_DIR, "debug_bbox")


def _debug_save(img_bgr, name: str):
    """
    Save debug images only if DEBUG=True.

    Parameters
    ----------
    img_bgr : np.ndarray
        BGR image to save.
    name : str
        Output filename inside the debug directory.
    """
    if not DEBUG:
        return

    os.makedirs(_DEBUG_DIR, exist_ok=True)
    out_path = os.path.join(_DEBUG_DIR, name)

    if img_bgr is None or img_bgr.size == 0:
        print(f"[bbox_utils] WARNING: empty image for debug save: {name}")
        return

    ok = cv2.imwrite(out_path, img_bgr)
    if not ok:
        print(f"[bbox_utils] WARNING: cv2.imwrite failed for: {out_path}")
    else:
        print(f"[bbox_utils] Saved debug image: {out_path}")


# Hand bounding box from wrist -------------------------------------------------
def compute_hand_bbox_from_wrist(wrist_lm, img_w, img_h, box_scale=0.35):
    """
    Compute a square bounding box around a wrist landmark.

    Parameters
    ----------
    wrist_lm : mediapipe.framework.formats.landmark_pb2.NormalizedLandmark or None
        Wrist landmark in normalized coordinates.
    img_w : int
        Full image width.
    img_h : int
        Full image height.
    box_scale : float, optional
        Relative size of the bounding box based on image height.

    Returns
    -------
    tuple or None
        (x1, y1, x2, y2) pixel coordinates, or None if invalid.
    """
    if wrist_lm is None:
        return None

    wx = wrist_lm.x * img_w
    wy = wrist_lm.y * img_h

    box_size = int(img_h * box_scale)
    half = box_size // 2

    x1 = int(wx - half)
    y1 = int(wy - half)
    x2 = int(wx + half)
    y2 = int(wy + half)

    x1 = max(x1, 0)
    y1 = max(y1, 0)
    x2 = min(x2, img_w - 1)
    y2 = min(y2, img_h - 1)

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


# Person bounding box from pose landmarks -------------------------------------
def compute_person_bbox_from_pose(pose_landmarks, img_w, img_h, padding=0.1):
    """
    Compute a full-body bounding box from pose landmarks.

    Parameters
    ----------
    pose_landmarks : list of MediaPipe landmarks
        Pose landmarks in normalized coordinates.
    img_w : int
        Full image width.
    img_h : int
        Full image height.
    padding : float, optional
        Extra margin added around the bounding box.

    Returns
    -------
    tuple or None
        (x1, y1, x2, y2) pixel coordinates, or None if invalid.
    """
    xs, ys = [], []

    for lm in pose_landmarks:
        if hasattr(lm, "visibility") and lm.visibility < 0.3:
            continue
        xs.append(lm.x * img_w)
        ys.append(lm.y * img_h)

    if not xs or not ys:
        return None

    min_x = max(min(xs), 0)
    max_x = min(max(xs), img_w - 1)
    min_y = max(min(ys), 0)
    max_y = min(max(ys), img_h - 1)

    box_w = max_x - min_x
    box_h = max_y - min_y

    pad_x = box_w * padding
    pad_y = box_h * padding

    x1 = max(int(min_x - pad_x), 0)
    y1 = max(int(min_y - pad_y), 0)
    x2 = min(int(max_x + pad_x), img_w - 1)
    y2 = min(int(max_y + pad_y), img_h - 1)

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


# Torso bounding box -----------------------------------------------------------
def compute_torso_bbox(pose_landmarks, img_w, img_h, padding=0.15):
    """
    Compute a torso bounding box using shoulders and hips.

    Parameters
    ----------
    pose_landmarks : list of MediaPipe landmarks
        Pose landmarks in normalized coordinates.
    img_w : int
        Full image width.
    img_h : int
        Full image height.
    padding : float, optional
        Extra margin added around the bounding box.

    Returns
    -------
    tuple or None
        (x1, y1, x2, y2) pixel coordinates, or None if invalid.
    """
    SHOULDER_R = 12
    SHOULDER_L = 11
    HIP_R = 24
    HIP_L = 23

    try:
        pts = [
            pose_landmarks[SHOULDER_R],
            pose_landmarks[SHOULDER_L],
            pose_landmarks[HIP_R],
            pose_landmarks[HIP_L],
        ]
    except Exception:
        return None

    xs = [p.x * img_w for p in pts]
    ys = [p.y * img_h for p in pts]

    min_x = max(min(xs), 0)
    max_x = min(max(xs), img_w - 1)
    min_y = max(min(ys), 0)
    max_y = min(max(ys), img_h - 1)

    box_w = max_x - min_x
    box_h = max_y - min_y

    x1 = max(int(min_x - box_w * padding), 0)
    y1 = max(int(min_y - box_h * padding), 0)
    x2 = min(int(max_x + box_w * padding), img_w - 1)
    y2 = min(int(max_y + box_h * padding), img_h - 1)

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


# Pixel-space pose bounding box ------------------------------------------------
def compute_pose_bbox_px(schema_lms, img_w, img_h, padding=0.25):
    """
    Compute a pixel-space bounding box around the person based on schema landmarks.

    Parameters
    ----------
    schema_lms : list of dict
        Each dict contains:
        {id, name, x_norm, y_norm, x_px, y_px, ...}
    img_w : int
        Full image width.
    img_h : int
        Full image height.
    padding : float, optional
        Extra margin added around the bounding box.

    Returns
    -------
    tuple or None
        (x1, y1, x2, y2) pixel coordinates, or None if invalid.
    """
    if not schema_lms:
        return None

    xs = [lm["x_px"] for lm in schema_lms]
    ys = [lm["y_px"] for lm in schema_lms]

    if not xs or not ys:
        return None

    x1 = max(min(xs), 0)
    y1 = max(min(ys), 0)
    x2 = min(max(xs), img_w)
    y2 = min(max(ys), img_h)

    w = x2 - x1
    h = y2 - y1

    if w < 5 or h < 5:
        return None

    pad_w = w * padding
    pad_h = h * padding

    x1 = max(int(x1 - pad_w), 0)
    y1 = max(int(y1 - pad_h), 0)
    x2 = min(int(x2 + pad_w), img_w)
    y2 = min(int(y2 + pad_h), img_h)

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


# Crop extraction --------------------------------------------------------------
def extract_crop(img_rgb, x1, y1, x2, y2, debug_name=None):
    """
    Extract a crop from an RGB image.

    Parameters
    ----------
    img_rgb : np.ndarray
        Full RGB image.
    x1, y1, x2, y2 : int
        Pixel coordinates of the crop box.
    debug_name : str, optional
        If provided, the crop will be saved for debugging.

    Returns
    -------
    np.ndarray
        The cropped RGB image.
    """
    crop = img_rgb[y1:y2, x1:x2]

    if debug_name:
        _debug_save(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), debug_name)

    return crop


# Upscaling -------------------------------------------------------------------
def upscale_crop(crop_rgb, size=512, debug_name=None):
    """
    Upscale a crop to a fixed size for better model accuracy.

    Parameters
    ----------
    crop_rgb : np.ndarray
        Input RGB crop.
    size : int, optional
        Target width/height.
    debug_name : str, optional
        If provided, the upscaled crop will be saved for debugging.

    Returns
    -------
    np.ndarray
        Upscaled crop of shape (size, size).
    """
    up = cv2.resize(crop_rgb, (size, size), interpolation=cv2.INTER_CUBIC)

    if debug_name:
        _debug_save(cv2.cvtColor(up, cv2.COLOR_RGB2BGR), debug_name)

    return up


# Lighting enhancement ---------------------------------------------------------
def enhance_lighting(crop_rgb, clip=3.0, grid=8, debug_name=None):
    """
    Apply CLAHE to improve low-light hand/pose detection.

    Parameters
    ----------
    crop_rgb : np.ndarray
        Input RGB crop.
    clip : float, optional
        CLAHE clip limit.
    grid : int, optional
        Tile grid size for CLAHE.
    debug_name : str, optional
        If provided, the enhanced crop will be saved for debugging.

    Returns
    -------
    np.ndarray
        Enhanced RGB crop.
    """
    lab = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    cl = clahe.apply(l)

    enhanced = cv2.merge((cl, a, b))
    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

    if debug_name:
        _debug_save(cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR), debug_name)

    return enhanced_rgb


# Coordinate restoration -------------------------------------------------------
def restore_landmarks_to_full_image(hand_lms, x1, y1, crop_w, crop_h, img_w, img_h):
    """
    Convert normalized crop coordinates back to full-image normalized coordinates.

    Parameters
    ----------
    hand_lms : list of MediaPipe landmarks
        Landmarks in crop-normalized coordinates.
    x1, y1 : int
        Crop top-left corner in full-image pixels.
    crop_w, crop_h : int
        Crop dimensions in pixels.
    img_w, img_h : int
        Full image dimensions.

    Returns
    -------
    list of dict
        Restored landmarks with normalized full-image coordinates:
        {
            "id": int,
            "x": float,
            "y": float,
            "z": float
        }
    """
    restored = []

    for i, lm in enumerate(hand_lms):
        cx = float(lm.x) * crop_w
        cy = float(lm.y) * crop_h

        orig_x = (x1 + cx) / img_w
        orig_y = (y1 + cy) / img_h

        restored.append(
            {
                "id": i,
                "x": orig_x,
                "y": orig_y,
                "z": float(lm.z),
            }
        )

    return restored
