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
# Path: PoseDetectionServer/utils/crop_utils.py
# -----------------------------------------------------------------------------

"""
Shared utilities for crop extraction, upscaling, lighting enhancement, and
restoring landmark coordinates back to full-image space.

These helpers are used by all workers to ensure consistent handling of crops
during pose and hand refinement workflows. They include:

- extract_crop(): Extract a pixel-aligned crop from an RGB image.
- upscale_crop(): Resize a crop to a fixed resolution for model input.
- enhance_lighting(): Optional CLAHE-based lighting enhancement.
- restore_landmarks_to_full_image(): Convert crop-normalized coordinates back
  into full-image normalized coordinates.
- build_crop_metadata(): Construct standardized crop metadata for schema output.
"""

import cv2
import numpy as np

# Optional debug saving
DEBUG = False
DEBUG_DIR = "debug_bbox"


def _debug_save(img_rgb, name: str):
    """
    Save debug crops if DEBUG=True.

    Parameters
    ----------
    img_rgb : np.ndarray
        RGB image to save.
    name : str
        Filename to write inside the debug directory.
    """
    if not DEBUG:
        return

    import os

    os.makedirs(DEBUG_DIR, exist_ok=True)
    cv2.imwrite(f"{DEBUG_DIR}/{name}", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))


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
        _debug_save(crop, debug_name)

    return crop


# Upscaling -------------------------------------------------------------------
def upscale_crop(crop_rgb, size=512, debug_name=None):
    """
    Upscale a crop to a fixed size for better model accuracy.

    Parameters
    ----------
    crop_rgb : np.ndarray
        Input crop.
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
        _debug_save(up, debug_name)

    return up


# Lighting enhancement ---------------------------------------------------------
def enhance_lighting(crop_rgb, clip=3.0, grid=8, debug_name=None):
    """
    Apply CLAHE to improve low-light detection.

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
        _debug_save(enhanced_rgb, debug_name)

    return enhanced_rgb


# Coordinate restoration -------------------------------------------------------
def restore_landmarks_to_full_image(landmarks, x1, y1, crop_w, crop_h, img_w, img_h):
    """
    Convert normalized crop coordinates back to full-image normalized coordinates.

    Parameters
    ----------
    landmarks : list of MediaPipe landmarks
        Landmarks in crop-normalized coordinates (0–1 range).
    x1, y1 : int
        Crop top-left corner in full-image pixel coordinates.
    crop_w, crop_h : int
        Crop dimensions in pixels.
    img_w, img_h : int
        Full image dimensions in pixels.

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

    for idx, lm in enumerate(landmarks):
        cx = float(lm.x) * crop_w
        cy = float(lm.y) * crop_h

        orig_x = (x1 + cx) / img_w
        orig_y = (y1 + cy) / img_h

        restored.append(
            {
                "id": idx,
                "x": orig_x,
                "y": orig_y,
                "z": float(lm.z),
            }
        )

    return restored


# Crop metadata builder --------------------------------------------------------
def build_crop_metadata(x1, y1, x2, y2, crop_w, crop_h, upscaled_size=512):
    """
    Build a standardized crop metadata block.

    Parameters
    ----------
    x1, y1, x2, y2 : int
        Pixel coordinates of the crop box.
    crop_w, crop_h : int
        Crop dimensions in pixels.
    upscaled_size : int, optional
        Size to which the crop was upscaled.

    Returns
    -------
    dict
        Crop metadata for schema output.
    """
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "width": crop_w,
        "height": crop_h,
        "upscaled_to": [upscaled_size, upscaled_size],
    }
