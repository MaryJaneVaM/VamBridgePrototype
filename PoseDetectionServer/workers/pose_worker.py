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
# Path: pose_server/PoseDetectionServer/pose_worker.py
# -----------------------------------------------------------------------------

"""
Pose detection worker built on MediaPipe's Pose Landmarker.

This module implements a cropping‑enabled pose detection pipeline used by the
Pose Detection Server. It performs full‑frame pose detection, estimates a
bounding box, optionally refines the pose inside a crop, and restores refined
landmarks back into full‑image coordinates.

The output follows the unified schema shared across all workers, including:
- normalized and pixel‑space landmarks
- visibility masks
- completeness scores
- optional crop metadata
"""

import mediapipe as mp
import cv2

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from workers.base_worker import BaseWorker
from utils.landmark_utils import (
    convert_landmarks_to_schema,
    compute_visibility_mask,
    compute_completeness,
    compute_pose_bbox_norm,
)
from utils.schema_utils import build_pose_block, build_response
from utils.model_utils import resolve_model_path

from utils.bbox_utils import compute_pose_bbox_px
from utils.crop_utils import (
    extract_crop,
    upscale_crop,
    restore_landmarks_to_full_image,
    build_crop_metadata,
)


# MediaPipe landmark names (33 points)
POSE_LANDMARK_NAMES = {
    0: "NOSE",
    1: "LEFT_EYE_INNER",
    2: "LEFT_EYE",
    3: "LEFT_EYE_OUTER",
    4: "RIGHT_EYE_INNER",
    5: "RIGHT_EYE",
    6: "RIGHT_EYE_OUTER",
    7: "LEFT_EAR",
    8: "RIGHT_EAR",
    9: "MOUTH_LEFT",
    10: "MOUTH_RIGHT",
    11: "LEFT_SHOULDER",
    12: "RIGHT_SHOULDER",
    13: "LEFT_ELBOW",
    14: "RIGHT_ELBOW",
    15: "LEFT_WRIST",
    16: "RIGHT_WRIST",
    17: "LEFT_PINKY",
    18: "RIGHT_PINKY",
    19: "LEFT_INDEX",
    20: "RIGHT_INDEX",
    21: "LEFT_THUMB",
    22: "RIGHT_THUMB",
    23: "LEFT_HIP",
    24: "RIGHT_HIP",
    25: "LEFT_KNEE",
    26: "RIGHT_KNEE",
    27: "LEFT_ANKLE",
    28: "RIGHT_ANKLE",
    29: "LEFT_HEEL",
    30: "RIGHT_HEEL",
    31: "LEFT_FOOT_INDEX",
    32: "RIGHT_FOOT_INDEX",
}


class MediaPipePoseWorker(BaseWorker):
    """
    Pose detection worker using MediaPipe's Pose Landmarker.

    This worker performs:
    - full‑frame pose detection
    - bounding‑box estimation
    - optional crop‑based refinement
    - restoration of refined landmarks to full‑image coordinates

    Parameters
    ----------
    model_filename : str, optional
        Name of the MediaPipe model file to load.
    """

    def __init__(self, model_filename="pose_landmarker_heavy.task"):
        model_path = resolve_model_path(model_filename)
        super().__init__(source_name="pose", model_path=model_path)

        with open(model_path, "rb") as f:
            model_data = f.read()

        base_options = mp_python.BaseOptions(model_asset_buffer=model_data)

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.detector = vision.PoseLandmarker.create_from_options(options)

    # Main detection pipeline
    def detect(self, image_bytes):
        """
        Run pose detection with optional crop refinement.

        The pipeline consists of:
        1. Full‑frame pose detection
        2. Bounding‑box estimation
        3. Optional crop‑based refinement
        4. Landmark restoration to full‑image coordinates
        5. Unified schema output

        Parameters
        ----------
        image_bytes : bytes
            Encoded input image.

        Returns
        -------
        dict
            Unified response containing metadata, pose landmarks, visibility
            mask, completeness score, bounding box, and optional crop metadata.
        """
        img_rgb, meta = self.preprocess(image_bytes)
        if img_rgb is None:
            return meta

        img_h, img_w = img_rgb.shape[:2]

        # Stage 1: Full-frame detection
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        result = self.detector.detect(mp_image)

        if not result.pose_landmarks:
            meta["frame_valid"] = False
            return build_response(meta, pose_block=None)

        raw_lms = result.pose_landmarks[0]

        schema_lms = convert_landmarks_to_schema(
            [
                {
                    "id": idx,
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "confidence": float(lm.visibility),
                }
                for idx, lm in enumerate(raw_lms)
            ],
            POSE_LANDMARK_NAMES,
            img_w,
            img_h,
        )

        bbox_px = compute_pose_bbox_px(schema_lms, img_w, img_h, padding=0.25)

        # Fallback: no crop refinement
        if bbox_px is None:
            visibility_mask = compute_visibility_mask(schema_lms)
            completeness = compute_completeness(visibility_mask)
            bbox_norm = compute_pose_bbox_norm(schema_lms)

            meta["frame_valid"] = completeness > 0

            pose_block = build_pose_block(
                landmarks=schema_lms,
                visibility_mask=visibility_mask,
                completeness=completeness,
                bbox=bbox_norm,
                crop_meta=None,
            )
            return build_response(meta, pose_block=pose_block)

        # Stage 2: Crop refinement
        x1, y1, x2, y2 = bbox_px
        crop = extract_crop(img_rgb, x1, y1, x2, y2)
        upscaled = upscale_crop(crop, size=512)

        mp_crop = mp.Image(image_format=mp.ImageFormat.SRGB, data=upscaled)
        refined = self.detector.detect(mp_crop)

        if not refined.pose_landmarks:
            visibility_mask = compute_visibility_mask(schema_lms)
            completeness = compute_completeness(visibility_mask)
            bbox_norm = compute_pose_bbox_norm(schema_lms)

            meta["frame_valid"] = completeness > 0

            pose_block = build_pose_block(
                landmarks=schema_lms,
                visibility_mask=visibility_mask,
                completeness=completeness,
                bbox=bbox_norm,
                crop_meta=None,
            )
            return build_response(meta, pose_block=pose_block)

        refined_raw = refined.pose_landmarks[0]

        restored_refined = restore_landmarks_to_full_image(
            refined_raw,
            x1,
            y1,
            crop.shape[1],
            crop.shape[0],
            img_w,
            img_h,
        )

        schema_refined = convert_landmarks_to_schema(
            [
                {
                    "id": idx,
                    "x": lm["x"],
                    "y": lm["y"],
                    "z": lm["z"],
                    "confidence": 1.0,
                }
                for idx, lm in enumerate(restored_refined)
            ],
            POSE_LANDMARK_NAMES,
            img_w,
            img_h,
        )

        visibility_mask = compute_visibility_mask(schema_refined)
        completeness = compute_completeness(visibility_mask)
        bbox_norm = compute_pose_bbox_norm(schema_refined)

        meta["frame_valid"] = completeness > 0

        crop_meta = build_crop_metadata(
            x1,
            y1,
            x2,
            y2,
            crop_w=crop.shape[1],
            crop_h=crop.shape[0],
        )

        pose_block = build_pose_block(
            landmarks=schema_refined,
            visibility_mask=visibility_mask,
            completeness=completeness,
            bbox=bbox_norm,
            crop_meta=crop_meta,
        )

        return build_response(meta, pose_block=pose_block)
