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
# Path: PoseDetectionServer/workers/holistic_worker.py
# -----------------------------------------------------------------------------

"""
Holistic detection worker built on MediaPipe's legacy Holistic API.

This module provides a cropping‑enabled holistic detection pipeline used by the
Pose Detection Server. It performs full‑frame detection of pose and hands,
estimates a pose‑based bounding box, optionally refines both pose and hand
landmarks inside a crop, and restores refined landmarks back into full‑image
coordinates.

The output follows the unified schema shared across all workers, including:
- pose landmarks
- left and right hand landmarks
- visibility masks
- completeness scores
- optional crop metadata
"""

import mediapipe as mp
import cv2

from workers.base_worker import BaseWorker
from utils.landmark_utils import (
    convert_landmarks_to_schema,
    compute_visibility_mask,
    compute_completeness,
    compute_pose_bbox_norm,
)
from utils.schema_utils import (
    build_pose_block,
    build_hand_block,
    build_response,
)

from utils.bbox_utils import compute_pose_bbox_px
from utils.crop_utils import (
    extract_crop,
    upscale_crop,
    restore_landmarks_to_full_image,
    build_crop_metadata,
)


# Pose landmark names (33 points)
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

# Hand landmark names (21 points)
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


class MediaPipeHolisticWorker(BaseWorker):
    """
    Holistic detection worker using MediaPipe's legacy Holistic API.

    This worker performs:
    - full‑frame holistic detection (pose + hands)
    - pose‑based bounding‑box estimation
    - optional crop‑based refinement
    - restoration of refined pose and hand landmarks to full‑image coordinates

    The output is formatted using the unified schema shared across all workers.
    """

    def __init__(self):
        super().__init__(source_name="holistic", model_path="mediapipe_holistic_v1")

        self.holistic = mp.solutions.holistic.Holistic(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=False,
            refine_face_landmarks=False,
        )

    # Main detection pipeline
    def detect(self, image_bytes):
        """
        Run holistic detection with optional crop refinement.

        The pipeline consists of:
        1. Full‑frame holistic detection (pose + hands)
        2. Pose‑based bounding‑box estimation
        3. Optional crop‑based refinement
        4. Restoration of refined landmarks to full‑image coordinates
        5. Unified schema output

        Parameters
        ----------
        image_bytes : bytes
            Encoded input image.

        Returns
        -------
        dict
            Unified response containing metadata, pose landmarks, hand landmarks,
            visibility masks, completeness scores, bounding boxes, and optional
            crop metadata.
        """
        img_rgb, meta = self.preprocess(image_bytes)
        if img_rgb is None:
            return meta

        img_h, img_w = img_rgb.shape[:2]

        # Stage 1: Full-frame holistic detection
        results = self.holistic.process(img_rgb)

        if not results.pose_landmarks:
            meta["frame_valid"] = False
            return build_response(meta, pose_block=None)

        raw_pose_lms = results.pose_landmarks.landmark

        schema_pose = convert_landmarks_to_schema(
            [
                {"id": i, "x": lm.x, "y": lm.y, "z": lm.z, "confidence": lm.visibility}
                for i, lm in enumerate(raw_pose_lms)
            ],
            POSE_LANDMARK_NAMES,
            img_w,
            img_h,
        )

        bbox_px = compute_pose_bbox_px(schema_pose, img_w, img_h, padding=0.25)

        # Fallback: no crop refinement
        if bbox_px is None:
            return self._build_full_frame_output(
                meta, results, schema_pose, img_w, img_h
            )

        # Stage 2: Crop refinement
        x1, y1, x2, y2 = bbox_px
        crop = extract_crop(img_rgb, x1, y1, x2, y2)
        upscaled = upscale_crop(crop, size=512)

        refined = self.holistic.process(upscaled)

        if not refined.pose_landmarks:
            return self._build_full_frame_output(
                meta, results, schema_pose, img_w, img_h
            )

        # Restore refined pose
        refined_pose_raw = refined.pose_landmarks.landmark

        restored_pose = restore_landmarks_to_full_image(
            refined_pose_raw,
            x1,
            y1,
            crop.shape[1],
            crop.shape[0],
            img_w,
            img_h,
        )

        schema_pose_refined = convert_landmarks_to_schema(
            [
                {"id": i, "x": lm["x"], "y": lm["y"], "z": lm["z"], "confidence": 1.0}
                for i, lm in enumerate(restored_pose)
            ],
            POSE_LANDMARK_NAMES,
            img_w,
            img_h,
        )

        vis_mask = compute_visibility_mask(schema_pose_refined)
        completeness = compute_completeness(vis_mask)
        bbox_norm = compute_pose_bbox_norm(schema_pose_refined)

        crop_meta = build_crop_metadata(
            x1,
            y1,
            x2,
            y2,
            crop_w=crop.shape[1],
            crop_h=crop.shape[0],
            upscaled_size=512,
        )

        pose_block = build_pose_block(
            landmarks=schema_pose_refined,
            visibility_mask=vis_mask,
            completeness=completeness,
            bbox=bbox_norm,
            crop_meta=crop_meta,
        )

        # Restore refined hands
        hand_left = None
        hand_right = None

        if refined.left_hand_landmarks:
            raw = refined.left_hand_landmarks.landmark

            restored = restore_landmarks_to_full_image(
                raw, x1, y1, crop.shape[1], crop.shape[0], img_w, img_h
            )

            schema_l = convert_landmarks_to_schema(
                [
                    {
                        "id": i,
                        "x": lm["x"],
                        "y": lm["y"],
                        "z": lm["z"],
                        "confidence": 1.0,
                    }
                    for i, lm in enumerate(restored)
                ],
                HAND_LANDMARK_NAMES,
                img_w,
                img_h,
            )
            completeness_l = compute_completeness([True] * len(schema_l))

            hand_left = build_hand_block(
                landmarks=schema_l,
                completeness=completeness_l,
                crop_meta=crop_meta,
                handedness_label="Left",
                handedness_conf=None,
            )

        if refined.right_hand_landmarks:
            raw = refined.right_hand_landmarks.landmark

            restored = restore_landmarks_to_full_image(
                raw, x1, y1, crop.shape[1], crop.shape[0], img_w, img_h
            )

            schema_r = convert_landmarks_to_schema(
                [
                    {
                        "id": i,
                        "x": lm["x"],
                        "y": lm["y"],
                        "z": lm["z"],
                        "confidence": 1.0,
                    }
                    for i, lm in enumerate(restored)
                ],
                HAND_LANDMARK_NAMES,
                img_w,
                img_h,
            )
            completeness_r = compute_completeness([True] * len(schema_r))

            hand_right = build_hand_block(
                landmarks=schema_r,
                completeness=completeness_r,
                crop_meta=crop_meta,
                handedness_label="Right",
                handedness_conf=None,
            )

        # Frame validity
        any_valid = (
            (pose_block and pose_block["completeness"] > 0)
            or (hand_left and hand_left["completeness"] > 0)
            or (hand_right and hand_right["completeness"] > 0)
        )
        meta["frame_valid"] = bool(any_valid)

        # Final unified response
        return build_response(
            meta,
            pose_block=pose_block,
            hand_left_block=hand_left,
            hand_right_block=hand_right,
        )

    # Helper: fallback full-frame output
    def _build_full_frame_output(self, meta, results, schema_pose, img_w, img_h):
        """
        Build holistic output without crop refinement.

        Parameters
        ----------
        meta : dict
            Frame metadata.
        results : mediapipe.HolisticResults
            Full‑frame holistic detection results.
        schema_pose : list
            Pose landmarks in unified schema format.
        img_w : int
            Image width.
        img_h : int
            Image height.

        Returns
        -------
        dict
            Unified response containing pose and hand landmarks without crop
            refinement.
        """
        vis_mask = compute_visibility_mask(schema_pose)
        completeness = compute_completeness(vis_mask)
        bbox_norm = compute_pose_bbox_norm(schema_pose)

        pose_block = build_pose_block(
            landmarks=schema_pose,
            visibility_mask=vis_mask,
            completeness=completeness,
            bbox=bbox_norm,
            crop_meta=None,
        )

        hand_left = None
        hand_right = None

        if results.left_hand_landmarks:
            raw = results.left_hand_landmarks.landmark
            schema_l = convert_landmarks_to_schema(
                [
                    {"id": i, "x": lm.x, "y": lm.y, "z": lm.z, "confidence": 1.0}
                    for i, lm in enumerate(raw)
                ],
                HAND_LANDMARK_NAMES,
                img_w,
                img_h,
            )
            completeness_l = compute_completeness([True] * len(schema_l))
            hand_left = build_hand_block(
                landmarks=schema_l,
                completeness=completeness_l,
                crop_meta=None,
                handedness_label="Left",
                handedness_conf=None,
            )

        if results.right_hand_landmarks:
            raw = results.right_hand_landmarks.landmark
            schema_r = convert_landmarks_to_schema(
                [
                    {"id": i, "x": lm.x, "y": lm.y, "z": lm.z, "confidence": 1.0}
                    for i, lm in enumerate(raw)
                ],
                HAND_LANDMARK_NAMES,
                img_w,
                img_h,
            )
            completeness_r = compute_completeness([True] * len(schema_r))
            hand_right = build_hand_block(
                landmarks=schema_r,
                completeness=completeness_r,
                crop_meta=None,
                handedness_label="Right",
                handedness_conf=None,
            )

        any_valid = (
            (pose_block and pose_block["completeness"] > 0)
            or (hand_left and hand_left["completeness"] > 0)
            or (hand_right and hand_right["completeness"] > 0)
        )
        meta["frame_valid"] = bool(any_valid)

        return build_response(
            meta,
            pose_block=pose_block,
            hand_left_block=hand_left,
            hand_right_block=hand_right,
        )
