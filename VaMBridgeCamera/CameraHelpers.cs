// -----------------------------------------------------------------------------
// Project: VaMBridgeCamera
// Component: CameraHelpers.cs (Virt-a-Mate Plugin - Camera Bridge Utilities)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgeCamera/CameraHelpers.cs
// -----------------------------------------------------------------------------

// Short script description.
// Minimal helper utilities for the VaM WindowCamera, including safe screenshot
// capture, view application, and view reading. Designed for coroutine-based
// capture and reliable camera activation.

using UnityEngine;
using System;
using System.Collections;

public static class CameraHelpers
{
  /// <summary>
  /// Ensures the WindowCamera is fully active and ready for use.
  /// Turns on the VaM WindowCamera via its CameraControl storable
  /// and enables the underlying Unity Camera named "MainWindowCamera".
  /// Required for correct FOV reporting and reliable screenshot capture.
  /// Safe to call multiple times; performs no action if already active.
  /// </summary>
  public static void EnsureCameraActive(Atom atom)
  {
    if (atom == null || atom.type != "WindowCamera") return;

    // Turn on WindowCamera via its storable
    JSONStorable camControl = atom.GetStorableByID("CameraControl") as JSONStorable;
    if (camControl != null)
    {
      camControl.SetBoolParamValue("cameraOn", true);
    }

    // Ensure underlying Unity camera is enabled
    Camera[] cams = GameObject.FindObjectsOfType<Camera>();
    foreach (var cam in cams)
    {
      if (cam.name == "MainWindowCamera")
      {
        if (!cam.enabled)
          cam.enabled = true;
        break;
      }
    }
  }

  /// <summary>
  /// Coroutine-based safe screenshot capture for WindowCamera.
  /// Invokes the provided callback with base64 image data when ready.
  /// </summary>
  public static IEnumerator CaptureScreenshotCoroutine(Atom atom, Action<string> onCapturedBase64)
  {
    if (onCapturedBase64 == null) yield break;

    if (atom == null || atom.type != "WindowCamera")
    {
      onCapturedBase64(null);
      yield break;
    }

    Camera winCam = atom.gameObject.GetComponentInChildren<Camera>(true);
    if (winCam == null)
    {
      onCapturedBase64(null);
      yield break;
    }

    int width = Screen.width;
    int height = Screen.height;
    if (width <= 0 || height <= 0)
    {
      onCapturedBase64(null);
      yield break;
    }

    RenderTexture rt = new RenderTexture(width, height, 24);
    winCam.targetTexture = rt;

    // Wait until end of frame to let Unity/VaM settle
    yield return new WaitForEndOfFrame();

    winCam.Render();

    RenderTexture.active = rt;
    Texture2D screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
    screenshot.ReadPixels(new Rect(0, 0, width, height), 0, 0);
    screenshot.Apply();

    winCam.targetTexture = null;
    RenderTexture.active = null;
    UnityEngine.Object.Destroy(rt);

    try
    {
      byte[] imageData = ImageConversion.EncodeToPNG(screenshot);
      string base64 = (imageData != null && imageData.Length > 0)
        ? Convert.ToBase64String(imageData)
        : null;

      onCapturedBase64(base64);
    }
    finally
    {
      if (screenshot != null) UnityEngine.Object.Destroy(screenshot);
    }
  }

  /// <summary>
  /// Applies a position and rotation to the WindowCamera atom.
  /// </summary>
  public static void ApplyView(Atom atom, Vector3 position, Quaternion rotation)
  {
    if (atom == null || atom.type != "WindowCamera") return;

    FreeControllerV3 control = atom.GetStorableByID("control") as FreeControllerV3;
    if (control == null) return;

    control.transform.position = position;
    control.transform.rotation = rotation;
  }

  /// <summary>
  /// Reads the current position and rotation of the WindowCamera atom.
  /// Uses out parameters instead of tuples (C# 6 compatible).
  /// </summary>
  public static void ReadView(Atom atom, out Vector3 position, out Quaternion rotation)
  {
    position = Vector3.zero;
    rotation = Quaternion.identity;

    if (atom == null || atom.type != "WindowCamera") return;

    FreeControllerV3 control = atom.GetStorableByID("control") as FreeControllerV3;
    if (control == null) return;

    position = control.transform.position;
    rotation = control.transform.rotation;
  }
}
