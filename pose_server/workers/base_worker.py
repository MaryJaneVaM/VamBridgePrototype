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
# Path: pose_server/workers/base_worker.py
# -----------------------------------------------------------------------------

"""
Shared base class for all MediaPipe workers (Pose, Hands, Holistic).

This module provides the common preprocessing pipeline used across all workers:
- decoding raw image bytes
- smart resizing while preserving aspect ratio
- computing resize scale
- converting BGR → RGB
- building the metadata block used by the unified schema

Workers extend this class to implement their own detection logic while relying
on consistent preprocessing and metadata handling.
"""

import cv2
import numpy as np

from utils.schema_utils import build_meta


class BaseWorker:
    """
    Base class providing shared preprocessing and metadata logic
    for all MediaPipe workers.

    Parameters
    ----------
    source_name : str
        Identifier for the worker type ("pose", "hands", or "holistic").
    model_path : str
        Absolute path to the .task model file used by the worker.
    """

    def __init__(self, source_name: str, model_path: str):
        self.source_name = source_name
        self.model_path = model_path

    # Image decoding + resizing
    def decode_image(self, image_bytes):
        """
        Decode raw PNG/JPEG bytes into a BGR image.

        Parameters
        ----------
        image_bytes : bytes
            Encoded image data.

        Returns
        -------
        np.ndarray or None
            Decoded BGR image, or None if decoding fails.
        """
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img_bgr

    def smart_resize(self, img_bgr, max_dim=2048):
        """
        Resize an image so its longest side is <= max_dim.

        Parameters
        ----------
        img_bgr : np.ndarray
            Input BGR image.
        max_dim : int, optional
            Maximum allowed size for the longest side.

        Returns
        -------
        resized : np.ndarray
            Resized image.
        scale : float
            Scale factor applied to the original image.
        """
        h, w = img_bgr.shape[:2]
        largest = max(h, w)

        if largest <= max_dim:
            return img_bgr, 1.0

        scale = max_dim / largest
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    # Preprocessing pipeline
    def preprocess(self, image_bytes):
        """
        Full preprocessing pipeline:
        - decode bytes
        - smart resize
        - compute resize scale
        - convert BGR → RGB
        - build metadata block

        Parameters
        ----------
        image_bytes : bytes
            Encoded input image.

        Returns
        -------
        img_rgb : np.ndarray or None
            Preprocessed RGB image, or None if decoding fails.
        meta : dict
            Metadata block used by the unified schema.
        """
        img_bgr = self.decode_image(image_bytes)
        if img_bgr is None:
            return None, {"error": "invalid_image"}

        # Resize
        img_bgr, resize_scale = self.smart_resize(img_bgr, max_dim=2048)

        # Convert to RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        img_h, img_w = img_rgb.shape[:2]

        # Build metadata block (frame_valid is updated by workers)
        meta = build_meta(
            source=self.source_name,
            model=self.model_path,
            img_w=img_w,
            img_h=img_h,
            resize_scale=resize_scale,
            frame_valid=True,
        )

        return img_rgb, meta

    # Helper: update frame_valid in meta
    def set_frame_valid(self, meta, is_valid: bool):
        """
        Update the frame_valid flag inside the metadata block.

        Parameters
        ----------
        meta : dict
            Metadata dictionary.
        is_valid : bool
            Whether the frame contains valid detections.
        """
        meta["frame_valid"] = bool(is_valid)

    # Helper: attach crop metadata
    def attach_crop_meta(self, meta, crop_meta):
        """
        Attach crop metadata to the meta block.

        Parameters
        ----------
        meta : dict
            Metadata dictionary.
        crop_meta : dict
            Crop metadata block.
        """
        meta["crop"] = crop_meta
