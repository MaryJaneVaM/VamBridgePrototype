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
# Path: pose_server/utils/schema_utils.py
# -----------------------------------------------------------------------------

"""
Unified schema builders for Pose, Hand, and Holistic workers.

This module defines the standardized output structures used across all workers.
Each worker produces:
- a metadata block describing the input frame and preprocessing
- optional pose, left-hand, and right-hand blocks
- a final unified response dictionary

These helpers ensure that all workers return consistent, predictable output
shapes regardless of the underlying MediaPipe model or detection pipeline.
"""


# Metadata block --------------------------------------------------------------
def build_meta(
    source: str,
    model: str,
    img_w: int,
    img_h: int,
    resize_scale: float,
    frame_valid: bool,
):
    """
    Build the metadata block shared by all workers.

    Parameters
    ----------
    source : str
        Worker type ("pose", "hands", or "holistic").
    model : str
        Path to the model file used by the worker.
    img_w : int
        Width of the processed image.
    img_h : int
        Height of the processed image.
    resize_scale : float
        Scale factor applied during smart resizing.
    frame_valid : bool
        Whether the frame contains valid detections.

    Returns
    -------
    dict
        Metadata dictionary describing the input frame and preprocessing.
    """
    aspect_ratio = img_w / img_h if img_h > 0 else None

    return {
        "source": source,
        "model": model,
        "image": {
            "width": img_w,
            "height": img_h,
            "aspect_ratio": aspect_ratio,
        },
        "resize_scale": resize_scale,
        "frame_valid": frame_valid,
    }


# Pose block ------------------------------------------------------------------
def build_pose_block(landmarks, visibility_mask, completeness, bbox, crop_meta):
    """
    Build the pose block according to the unified schema.

    Parameters
    ----------
    landmarks : list or None
        Pose landmarks in unified schema format.
    visibility_mask : list of bool
        Visibility mask for each landmark.
    completeness : float
        Fraction of visible landmarks.
    bbox : dict or None
        Normalized bounding box for the pose.
    crop_meta : dict or None
        Crop metadata used during refinement.

    Returns
    -------
    dict or None
        Pose block, or None if no landmarks are provided.
    """
    if landmarks is None:
        return None

    return {
        "landmarks": landmarks,
        "visibility_mask": visibility_mask,
        "completeness": completeness,
        "bbox": bbox,
        "crop": crop_meta,
    }


# Hand block ------------------------------------------------------------------
def build_hand_block(
    landmarks,
    completeness,
    crop_meta,
    handedness_label,
    handedness_conf,
):
    """
    Build a hand block (left or right) according to the unified schema.

    Parameters
    ----------
    landmarks : list or None
        Hand landmarks in unified schema format.
    completeness : float
        Fraction of visible landmarks (hands always assume full visibility).
    crop_meta : dict or None
        Crop metadata used during refinement.
    handedness_label : str
        "Left" or "Right".
    handedness_conf : float or None
        Confidence score for handedness classification.

    Returns
    -------
    dict or None
        Hand block, or None if no landmarks are provided.
    """
    if landmarks is None:
        return None

    return {
        "handedness": handedness_label,
        "handedness_confidence": handedness_conf,
        "landmarks": landmarks,
        "completeness": completeness,
        "crop": crop_meta,
    }


# Final response --------------------------------------------------------------
def build_response(meta, pose_block=None, hand_left_block=None, hand_right_block=None):
    """
    Build the final unified response structure.

    Parameters
    ----------
    meta : dict
        Metadata block.
    pose_block : dict or None
        Pose block.
    hand_left_block : dict or None
        Left-hand block.
    hand_right_block : dict or None
        Right-hand block.

    Returns
    -------
    dict
        Unified response containing metadata and all available detection blocks.
    """
    return {
        "meta": meta,
        "pose": pose_block,
        "hand_left": hand_left_block,
        "hand_right": hand_right_block,
    }
