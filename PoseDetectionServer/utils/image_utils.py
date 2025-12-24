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
# Path: PoseDetectionServer/utils/image_utils.py
# -----------------------------------------------------------------------------

"""
Utility functions for image preprocessing.

This module provides helpers used by multiple workers to ensure consistent
image handling. Currently includes:

- smart_resize(): Resize an image so its longest side does not exceed a
  configurable maximum, while preserving aspect ratio.

These utilities help prevent extremely large inputs from slowing down
MediaPipe pipelines.
"""

import cv2
import numpy as np


def smart_resize(img, max_dim=2048):
    """
    Resize an image so that its longest side is <= max_dim.

    This prevents extremely large inputs from slowing down MediaPipe while
    preserving the original aspect ratio.

    Parameters
    ----------
    img : np.ndarray
        Input BGR image.
    max_dim : int, optional
        Maximum allowed size for the longest side.

    Returns
    -------
    np.ndarray
        Resized image. If no resizing is needed, the original image is returned.
    """
    h, w = img.shape[:2]
    largest = max(h, w)

    if largest <= max_dim:
        return img

    scale = max_dim / largest
    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
