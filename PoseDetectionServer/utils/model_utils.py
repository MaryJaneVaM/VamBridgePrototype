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
# Path: PoseDetectionServer/utils/model_utils.py
# -----------------------------------------------------------------------------

"""
Utility functions for resolving MediaPipe model paths.

This module provides helpers for locating `.task` model files used by all
MediaPipe Tasks API workers. Paths are resolved relative to the project root
(`pose_server/`) and normalized to forward slashes for compatibility with
MediaPipe's C++ backend, especially on Windows.
"""

import os


def resolve_model_path(model_filename: str) -> str:
    """
    Build an absolute, MediaPipe‑friendly path to a `.task` model file.

    The path is constructed relative to the project root (`pose_server/`)
    regardless of the current working directory. On Windows, all backslashes
    are converted to forward slashes to avoid issues with MediaPipe's C++
    backend.

    Parameters
    ----------
    model_filename : str
        Name of the model file (e.g., "pose_landmarker_heavy.task").

    Returns
    -------
    str
        Absolute filesystem path to the model, normalized to forward slashes.
    """
    # Base directory: pose_server/
    base_dir = os.path.dirname(os.path.dirname(__file__))

    # pose_server/models/<model_filename>
    model_path = os.path.join(base_dir, "models", model_filename)

    # Absolute path + normalize to forward slashes (critical for Windows)
    model_path = os.path.abspath(model_path).replace("\\", "/")

    return model_path
