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
# Path: PoseDetectionServer/routes/pose_route.py
# -----------------------------------------------------------------------------

"""
Flask route for the MediaPipe Pose Landmarker worker (Tasks API v2).

This module exposes the `/detect/pose` endpoint, which accepts raw PNG/JPEG
image bytes and returns a unified pose detection response. It supports:

- POST  → run pose detection
- GET   → return endpoint information
- OPTIONS → CORS preflight

The response follows the unified schema used across all workers.
"""

from flask import Blueprint, request, jsonify, make_response
from workers.pose_worker import MediaPipePoseWorker

# Blueprint for modular routing
pose_bp = Blueprint("pose", __name__)

# Initialize worker once for efficiency
pose_worker = MediaPipePoseWorker()


# CORS headers ----------------------------------------------------------------
@pose_bp.after_request
def add_cors_headers(response):
    """
    Add permissive CORS headers to all responses.

    Parameters
    ----------
    response : flask.Response
        Outgoing response object.

    Returns
    -------
    flask.Response
        Modified response with CORS headers.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response


# OPTIONS ---------------------------------------------------------------------
@pose_bp.route("/detect/pose", methods=["OPTIONS"])
def pose_options():
    """
    Handle browser CORS preflight requests.

    Returns
    -------
    flask.Response
        Empty 200 OK response.
    """
    return make_response("", 200)


# GET -------------------------------------------------------------------------
@pose_bp.route("/detect/pose", methods=["GET"])
def pose_info():
    """
    Return basic endpoint information.

    Returns
    -------
    tuple
        JSON response and HTTP status code.
    """
    return (
        jsonify(
            {
                "info": (
                    "Send a POST request with image bytes to this endpoint "
                    "for pose detection."
                )
            }
        ),
        200,
    )


# POST ------------------------------------------------------------------------
@pose_bp.route("/detect/pose", methods=["POST"])
def pose_detect():
    """
    Run pose detection on incoming image bytes.

    Expects raw PNG/JPEG bytes in the request body.

    Returns
    -------
    tuple
        JSON response containing the unified pose block and metadata,
        along with an HTTP status code.
    """
    image_bytes = request.data

    if not image_bytes:
        return jsonify({"error": "no_image_received"}), 400

    result = pose_worker.detect(image_bytes)
    return jsonify(result), 200
