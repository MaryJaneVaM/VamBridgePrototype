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
# Path: PoseDetectionServer/app.py
# -----------------------------------------------------------------------------

"""
Main Flask application for the Pose Detection Server.

This module initializes the Flask application and registers all detection
endpoints:

- /detect/holistic  → full-body + hands (legacy Holistic API)
- /detect/pose      → pose-only (Tasks API v2)
- /detect/hands     → hand-only (Tasks API v2)

All endpoints accept raw PNG/JPEG image bytes via POST and return results
following the unified schema used across all workers.
"""

# Reduce MediaPipe / absl / TFLite warning noise (Python-level only)
import os

os.environ["GLOG_minloglevel"] = "2"
os.environ["ABSL_MIN_LOG_LEVEL"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from flask import Flask, jsonify
from routes.holistic_route import holistic_bp
from routes.pose_route import pose_bp
from routes.hand_route import hand_bp


def create_app():
    """
    Create and configure the Flask application.

    Returns
    -------
    flask.Flask
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(holistic_bp)
    app.register_blueprint(pose_bp)
    app.register_blueprint(hand_bp)

    @app.route("/", methods=["GET"])
    def index():
        """
        Return basic server information.

        Returns
        -------
        tuple
            JSON response and HTTP status code.
        """
        return (
            jsonify(
                {
                    "server": "Pose Detection Server",
                    "endpoints": {
                        "holistic": "/detect/holistic",
                        "pose": "/detect/pose",
                        "hands": "/detect/hands",
                    },
                }
            ),
            200,
        )

    return app


if __name__ == "__main__":
    # Run development server
    app = create_app()
    app.run(host="127.0.0.1", port=5005, debug=False)
