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
# Path: PoseDetectionServer/workers/hand_worker.py
# -----------------------------------------------------------------------------

"""
Hand detection worker built on MediaPipe's Hand Landmarker.

This module provides a cropping‑enabled hand detection pipeline used by the
Pose Detection Server. It uses the Pose Landmarker to locate wrist positions,
computes hand‑specific bounding boxes, extracts crops, optionally upscales
them, and runs the Hand Landmarker to obtain refined hand landmarks.

The output follows the unified schema shared across all workers, including:
- left and right hand landmarks
- completeness scores
- handedness labels and confidence
- optional crop metadata
"""

import mediapipe as mp
import cv2

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from workers.base_worker import BaseWorker
from utils.crop_utils import (
    extract_crop,
    upscale_crop,
    restore_landmarks_to_full_image,
    build_crop_metadata,
)
from utils.landmark_utils import (
    convert_landmarks_to_schema,
    compute_visibility_mask,
    compute_completeness,
)
from utils.schema_utils import build_hand_block, build_response
from utils.model_utils import resolve_model_path
from utils.bbox_utils import compute_hand_bbox_from_wrist


# MediaPipe hand landmark names (21 points)
HAND_LANDMARK_NAMES = {
    0: "WRIST",
    1: "THUMB_CMC",
    2: "THUMB_MCP",
    3: "THUMB_IP",
    4: "THUMB_TIP",
    5: "INDEX_MCP",
    6: "INDEX_PIP",
    7: "INDEX_DIP",
    8: "INDEX_TIP",
    9: "MIDDLE_MCP",
    10: "MIDDLE_PIP",
    11: "MIDDLE_DIP",
    12: "MIDDLE_TIP",
    13: "RING_MCP",
    14: "RING_PIP",
    15: "RING_DIP",
    16: "RING_TIP",
    17: "PINKY_MCP",
    18: "PINKY_PIP",
    19: "PINKY_DIP",
    20: "PINKY_TIP",
}


class MediaPipeHandWorker(BaseWorker):
    """
    Hand detection worker using MediaPipe's Hand Landmarker.

    This worker performs:
    - wrist detection using the Pose Landmarker
    - hand bounding‑box estimation
    - crop extraction and optional upscaling
    - refined hand landmark detection
    - restoration of refined landmarks to full‑image coordinates

    The output is formatted using the unified schema shared across all workers.
    """

    def __init__(
        self,
        hand_model_filename="hand_landmarker.task",
        pose_model_filename="pose_landmarker_heavy.task",
    ):
        # Resolve model paths
        hand_model_path = resolve_model_path(hand_model_filename)
        pose_model_path = resolve_model_path(pose_model_filename)

        super().__init__(source_name="hands", model_path=hand_model_path)

        # Load Hand Landmarker
        with open(hand_model_path, "rb") as f:
            hand_model_data = f.read()

        hand_base = mp_python.BaseOptions(model_asset_buffer=hand_model_data)

        hand_options = vision.HandLandmarkerOptions(
            base_options=hand_base,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
        )

        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        # Load Pose Landmarker (for wrist detection)
        with open(pose_model_path, "rb") as f:
            pose_model_data = f.read()

        pose_base = mp_python.BaseOptions(model_asset_buffer=pose_model_data)

        pose_options = vision.PoseLandmarkerOptions(
            base_options=pose_base,
            running_mode=vision.RunningMode.IMAGE,
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.pose_detector = vision.PoseLandmarker.create_from_options(pose_options)

    # Run hand detection on a crop
    def _detect_single_hand(self, crop_rgb, x1, y1, x2, y2, img_w, img_h, handedness):
        """
        Detect a single hand inside a cropped region.

        Parameters
        ----------
        crop_rgb : np.ndarray
            RGB crop containing the hand.
        x1, y1, x2, y2 : int
            Crop bounding box coordinates in the full image.
        img_w : int
            Full image width.
        img_h : int
            Full image height.
        handedness : str
            "Left" or "Right".

        Returns
        -------
        dict or None
            Hand block in unified schema format, or None if detection fails.
        """
        crop_h, crop_w = crop_rgb.shape[:2]

        if crop_w < 32 or crop_h < 32:
            return None

        # Upscale crop
        upscaled = upscale_crop(crop_rgb, size=512)

        # Run hand detection
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=upscaled)
        result = self.hand_detector.detect(mp_image)

        if not result.hand_landmarks:
            return None

        hand_lms = result.hand_landmarks[0]

        # Restore normalized coordinates
        restored = restore_landmarks_to_full_image(
            hand_lms, x1, y1, crop_w, crop_h, img_w, img_h
        )

        # Convert to schema format
        schema_lms = convert_landmarks_to_schema(
            restored, HAND_LANDMARK_NAMES, img_w, img_h
        )

        # Visibility + completeness
        visibility_mask = compute_visibility_mask(schema_lms)
        completeness = compute_completeness(visibility_mask)

        # Crop metadata
        crop_meta = build_crop_metadata(x1, y1, x2, y2, crop_w, crop_h)

        # Handedness confidence
        handedness_conf = (
            float(result.handedness[0][0].score) if result.handedness else None
        )

        return build_hand_block(
            landmarks=schema_lms,
            completeness=completeness,
            crop_meta=crop_meta,
            handedness_label=handedness,
            handedness_conf=handedness_conf,
        )

    # Main detection pipeline
    def detect(self, image_bytes):
        """
        Run hand detection using wrist‑based bounding boxes.

        The pipeline consists of:
        1. Pose detection to locate wrist positions
        2. Hand bounding‑box estimation
        3. Crop extraction and optional upscaling
        4. Hand landmark detection
        5. Unified schema output

        Parameters
        ----------
        image_bytes : bytes
            Encoded input image.

        Returns
        -------
        dict
            Unified response containing left and right hand blocks.
        """
        img_rgb, meta = self.preprocess(image_bytes)
        if img_rgb is None:
            return meta

        img_h, img_w = img_rgb.shape[:2]

        # Detect pose to find wrists
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        pose_result = self.pose_detector.detect(mp_image)

        if not pose_result.pose_landmarks:
            meta["frame_valid"] = False
            return build_response(meta, pose_block=None)

        pose_lms = pose_result.pose_landmarks[0]

        # Wrist indices
        RIGHT_WRIST = 15
        LEFT_WRIST = 16

        right_wrist = pose_lms[RIGHT_WRIST] if len(pose_lms) > RIGHT_WRIST else None
        left_wrist = pose_lms[LEFT_WRIST] if len(pose_lms) > LEFT_WRIST else None

        # Compute bounding boxes
        hands = {"left": None, "right": None}

        # Right hand
        right_bbox = compute_hand_bbox_from_wrist(right_wrist, img_w, img_h)
        if right_bbox:
            rx1, ry1, rx2, ry2 = right_bbox
            crop = extract_crop(img_rgb, rx1, ry1, rx2, ry2)
            hands["right"] = self._detect_single_hand(
                crop, rx1, ry1, rx2, ry2, img_w, img_h, handedness="Right"
            )

        # Left hand
        left_bbox = compute_hand_bbox_from_wrist(left_wrist, img_w, img_h)
        if left_bbox:
            lx1, ly1, lx2, ly2 = left_bbox
            crop = extract_crop(img_rgb, lx1, ly1, lx2, ly2)
            hands["left"] = self._detect_single_hand(
                crop, lx1, ly1, lx2, ly2, img_w, img_h, handedness="Left"
            )

        # Frame validity = at least one hand detected
        meta["frame_valid"] = bool(hands["left"] or hands["right"])

        return build_response(
            meta,
            pose_block=None,
            hand_left_block=hands["left"],
            hand_right_block=hands["right"],
        )
