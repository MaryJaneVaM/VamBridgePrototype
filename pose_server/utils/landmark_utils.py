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
# Path: pose_server/utils/landmark_utils.py
# -----------------------------------------------------------------------------

"""
Shared utilities for processing pose and hand landmarks.

This module provides helper functions used by all workers to ensure consistent
landmark processing and output formatting. It includes:

- visibility mask computation
- completeness scoring
- normalized bounding box generation (pose and hand)
- conversion of restored landmarks into the unified schema
- frame validity evaluation
"""

import numpy as np


# Visibility mask --------------------------------------------------------------
def compute_visibility_mask(landmarks, threshold=0.3):
    """
    Convert landmark confidence/visibility into a boolean mask.

    Parameters
    ----------
    landmarks : list of dict
        Each dict must contain a "confidence" field.
    threshold : float, optional
        Minimum confidence required for a landmark to be considered visible.

    Returns
    -------
    list of bool
        Boolean visibility mask for each landmark.
    """
    if not landmarks:
        return []

    return [lm.get("confidence", 0.0) >= threshold for lm in landmarks]


# Completeness score -----------------------------------------------------------
def compute_completeness(visibility_mask):
    """
    Compute completeness = ratio of visible landmarks.

    Parameters
    ----------
    visibility_mask : list of bool
        Visibility mask for each landmark.

    Returns
    -------
    float
        Completeness score in the range [0, 1].
    """
    if not visibility_mask:
        return 0.0

    visible = sum(1 for v in visibility_mask if v)
    return visible / len(visibility_mask)


# Normalized bounding box (pose) -----------------------------------------------
def compute_pose_bbox_norm(landmarks):
    """
    Compute a normalized bounding box from pose landmarks.

    Parameters
    ----------
    landmarks : list of dict
        Each dict must contain normalized coordinates "x_norm" and "y_norm".

    Returns
    -------
    dict or None
        Normalized bounding box with keys:
        {x1, y1, x2, y2, width_norm, height_norm}
    """
    if not landmarks:
        return None

    xs = [lm["x_norm"] for lm in landmarks]
    ys = [lm["y_norm"] for lm in landmarks]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    return {
        "x1": min_x,
        "y1": min_y,
        "x2": max_x,
        "y2": max_y,
        "width_norm": max_x - min_x,
        "height_norm": max_y - min_y,
    }


# Normalized bounding box (hand) -----------------------------------------------
def compute_hand_bbox_norm(landmarks):
    """
    Compute a normalized bounding box for a hand.

    Parameters
    ----------
    landmarks : list of dict
        Each dict must contain normalized coordinates "x_norm" and "y_norm".

    Returns
    -------
    dict or None
        Normalized bounding box with keys:
        {x1, y1, x2, y2, width_norm, height_norm}
    """
    if not landmarks:
        return None

    xs = [lm["x_norm"] for lm in landmarks]
    ys = [lm["y_norm"] for lm in landmarks]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    return {
        "x1": min_x,
        "y1": min_y,
        "x2": max_x,
        "y2": max_y,
        "width_norm": max_x - min_x,
        "height_norm": max_y - min_y,
    }


# Convert restored landmarks into schema format --------------------------------
def convert_landmarks_to_schema(restored, names, img_w, img_h):
    """
    Convert restored landmarks into the unified schema format.

    Parameters
    ----------
    restored : list of dict
        Each dict contains:
        {id, x, y, z, confidence?} in normalized full-image coordinates.
    names : dict
        Mapping from landmark ID → landmark name.
    img_w : int
        Width of the processed image.
    img_h : int
        Height of the processed image.

    Returns
    -------
    list of dict
        Each dict contains:
        {
            id, name,
            x_norm, y_norm,
            x_px, y_px,
            z,
            confidence
        }
    """
    output = []

    for lm in restored:
        idx = lm["id"]
        x_norm = lm["x"]
        y_norm = lm["y"]

        output.append(
            {
                "id": idx,
                "name": names.get(idx, "UNKNOWN"),
                "x_norm": x_norm,
                "y_norm": y_norm,
                "x_px": x_norm * img_w,
                "y_px": y_norm * img_h,
                "z": lm["z"],
                "confidence": lm.get("confidence", 1.0),
            }
        )

    return output


# Frame validity ---------------------------------------------------------------
def compute_frame_valid(completeness, min_required=0.5):
    """
    Determine whether a frame is usable based on completeness.

    Parameters
    ----------
    completeness : float
        Ratio of visible landmarks.
    min_required : float, optional
        Minimum completeness required for the frame to be considered valid.

    Returns
    -------
    bool
        True if the frame meets the minimum completeness threshold.
    """
    return completeness >= min_required
