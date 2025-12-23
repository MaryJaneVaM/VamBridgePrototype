// -----------------------------------------------------------------------------
// Project: VaMBridgeCamera
// Component: VaMBridgeCamera.cs (Virt-a-Mate Plugin - Camera Bridge)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgeCamera/VaMBridgeCamera.cs
// -----------------------------------------------------------------------------

// Short script description.
// Minimal TCP bridge plugin enabling remote control of the VaM WindowCamera.
// Supports screenshot capture, reading camera view, and applying new views.

using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Collections;
using SimpleJSON;

public class VaMBridgeCamera : MVRScript
{
  private const string HOST = "127.0.0.1";
  private const int PORT = 5000;

  private Socket _client;
  private IAsyncResult _connectResult;
  private bool _connected;
  private bool _helloSent;
  private readonly byte[] _recvBuf = new byte[65536];

  private static bool _enableLogs = false;
  private string _atomName = "Unknown";

  private void Log(string message)
  {
    if (_enableLogs) SuperController.LogMessage(message);
  }

  private void LogError(string message)
  {
    if (_enableLogs) SuperController.LogError(message);
  }

  // Initialization -------------------------------------------------------------
  public override void Init()
  {
    if (containingAtom == null || containingAtom.type != "WindowCamera")
    {
      LogError("[VaMBridgeCamera] Must be attached to a WindowCamera atom.");
      return;
    }

    _atomName = containingAtom.name;

    CameraHelpers.EnsureCameraActive(containingAtom);

    try
    {
      _client = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp)
      { NoDelay = true };
      _connectResult = _client.BeginConnect(new IPEndPoint(IPAddress.Parse(HOST), PORT), null, null);
    }
    catch (Exception e)
    {
      LogError($"[VaMBridgeCamera] [{_atomName}] Init error: {e.Message}");
      Cleanup();
    }
  }

  // Update loop ---------------------------------------------------------------
  public void Update()
  {
    try
    {
      CompleteConnectionIfPending();

      if (_client == null || !_client.Connected) return;

      if (_connected && !_helloSent)
      {
        SendHello();
        _helloSent = true;
      }

      string json = SocketUtils.ReceiveFrame(_client, _recvBuf);
      if (string.IsNullOrEmpty(json)) return;

      JSONNode node = JSON.Parse(json);
      if (node == null || string.IsNullOrEmpty(node["cmd"])) return;

      string cmd = node["cmd"];
      switch (cmd)
      {
        case "screenshot":
          StartCoroutine(CaptureAndSendScreenshotCoroutine());
          break;

        case "read_view":
          SendReadViewResult();
          break;

        case "set_view":
          ApplyView(node["data"]);
          break;

        case "acknowledge":
          Log($"[VaMBridgeCamera] [{_atomName}] Handshake acknowledged by server");
          break;

        default:
          Log($"[VaMBridgeCamera] [{_atomName}] Unknown command: {cmd}");
          break;
      }
    }
    catch (Exception e)
    {
      LogError($"[VaMBridgeCamera] [{_atomName}] Update error: {e.Message}");
      Cleanup();
    }
  }

  // Connection handling --------------------------------------------------------
  private void CompleteConnectionIfPending()
  {
    if (!_connected && _client != null && _connectResult != null &&
        _connectResult.AsyncWaitHandle.WaitOne(0, true))
    {
      _client.EndConnect(_connectResult);
      _connectResult = null;
      _connected = _client.Connected;
      string ident = $"[VaMBridgeCamera] [{_atomName}]";
      Log(_connected ? $"{ident} TCP connected" : $"{ident} TCP connect failed");
    }
  }

  private void SendHello()
  {
    var node = new JSONClass();
    node["cmd"] = "hello";
    node["id"] = containingAtom.uid;
    node["name"] = containingAtom.name;
    SocketUtils.SendFrame(_client, node.ToString());
    Log($"[VaMBridgeCamera] [{_atomName}] Sent hello");
  }

  // Screenshot capture ---------------------------------------------------------
  private IEnumerator CaptureAndSendScreenshotCoroutine()
  {
    yield return CameraHelpers.CaptureScreenshotCoroutine(containingAtom, (string base64) =>
    {
      if (string.IsNullOrEmpty(base64)) return;
      SendScreenshotResult(base64);
    });
  }

  private float GetWindowCameraFov()
  {
    Camera[] cams = GameObject.FindObjectsOfType<Camera>();
    foreach (var cam in cams)
    {
      if (cam.name == "MainWindowCamera")
      {
        if (!cam.enabled) cam.enabled = true;
        return cam.fieldOfView;
      }
    }
    return 0f;
  }

  private void SendScreenshotResult(string base64)
  {
    Vector3 pos;
    Quaternion rot;
    CameraHelpers.ReadView(containingAtom, out pos, out rot);

    float fov = GetWindowCameraFov();

    var node = new JSONClass();
    node["cmd"] = "screenshot_result";
    node["id"] = containingAtom.uid;
    node["name"] = containingAtom.name;

    var data = new JSONClass();
    data["id"] = "control";
    data["imageBase64"] = base64;
    data["fov"] = fov.ToString();
    data["position"] = ToJson(pos);
    data["rotation"] = ToJson(rot);
    data["rotationEuler"] = ToJsonEuler(rot.eulerAngles);

    node["data"] = data;
    SocketUtils.SendFrame(_client, node.ToString());
  }

  // Read view ------------------------------------------------------------------
  private void SendReadViewResult()
  {
    Vector3 pos;
    Quaternion rot;
    CameraHelpers.ReadView(containingAtom, out pos, out rot);

    float fov = GetWindowCameraFov();

    var node = new JSONClass();
    node["cmd"] = "read_view_result";
    node["id"] = containingAtom.uid;
    node["name"] = containingAtom.name;

    var data = new JSONClass();
    data["id"] = "control";
    data["imageBase64"] = "";
    data["fov"] = fov.ToString();
    data["position"] = ToJson(pos);
    data["rotation"] = ToJson(rot);
    data["rotationEuler"] = ToJsonEuler(rot.eulerAngles);

    node["data"] = data;
    SocketUtils.SendFrame(_client, node.ToString());
  }

  // Apply view -----------------------------------------------------------------
  private void ApplyView(JSONNode data)
  {
    if (data == null) return;

    float px = data["position"]["x"].AsFloat;
    float py = data["position"]["y"].AsFloat;
    float pz = data["position"]["z"].AsFloat;
    Vector3 pos = new Vector3(px, py, pz);

    Quaternion rot;

    JSONNode rotNode = data["rotation"];
    bool hasValidQuat =
      rotNode != null &&
      rotNode["x"] != null && !string.IsNullOrEmpty(rotNode["x"].Value) &&
      rotNode["y"] != null && !string.IsNullOrEmpty(rotNode["y"].Value) &&
      rotNode["z"] != null && !string.IsNullOrEmpty(rotNode["z"].Value) &&
      rotNode["w"] != null && !string.IsNullOrEmpty(rotNode["w"].Value);

    if (hasValidQuat)
    {
      float qx = rotNode["x"].AsFloat;
      float qy = rotNode["y"].AsFloat;
      float qz = rotNode["z"].AsFloat;
      float qw = rotNode["w"].AsFloat;

      rot = new Quaternion(qx, qy, qz, qw);
    }
    else
    {
      JSONNode eulerNode = data["rotationEuler"];
      bool hasValidEuler =
        eulerNode != null &&
        eulerNode["x"] != null && !string.IsNullOrEmpty(eulerNode["x"].Value) &&
        eulerNode["y"] != null && !string.IsNullOrEmpty(eulerNode["y"].Value) &&
        eulerNode["z"] != null && !string.IsNullOrEmpty(eulerNode["z"].Value);

      if (!hasValidEuler) return;

      float rx = eulerNode["x"].AsFloat;
      float ry = eulerNode["y"].AsFloat;
      float rz = eulerNode["z"].AsFloat;

      rot = Quaternion.Euler(rx, ry, rz);
    }

    CameraHelpers.ApplyView(containingAtom, pos, rot);

    float fov = GetWindowCameraFov();

    var node = new JSONClass();
    node["cmd"] = "set_view_result";
    node["id"] = containingAtom.uid;
    node["name"] = containingAtom.name;

    var result = new JSONClass();
    result["id"] = "control";
    result["imageBase64"] = "";
    result["fov"] = fov.ToString();
    result["position"] = ToJson(pos);
    result["rotation"] = ToJson(rot);
    result["rotationEuler"] = ToJsonEuler(rot.eulerAngles);

    node["data"] = result;
    SocketUtils.SendFrame(_client, node.ToString());
  }

  // JSON helpers ---------------------------------------------------------------
  private JSONClass ToJson(Vector3 v)
  {
    var obj = new JSONClass();
    obj["x"] = v.x.ToString();
    obj["y"] = v.y.ToString();
    obj["z"] = v.z.ToString();
    return obj;
  }

  private JSONClass ToJson(Quaternion q)
  {
    var obj = new JSONClass();
    obj["x"] = q.x.ToString();
    obj["y"] = q.y.ToString();
    obj["z"] = q.z.ToString();
    obj["w"] = q.w.ToString();
    return obj;
  }

  private JSONClass ToJsonEuler(Vector3 euler)
  {
    var obj = new JSONClass();
    obj["x"] = euler.x.ToString();
    obj["y"] = euler.y.ToString();
    obj["z"] = euler.z.ToString();
    return obj;
  }

  // Cleanup --------------------------------------------------------------------
  private void OnDisable() { Cleanup(); }
  private void OnDestroy() { Cleanup(); }

  private void Cleanup()
  {
    string name = _atomName;
    try
    {
      if (_client != null)
      {
        if (_client.Connected)
        {
          try { _client.Shutdown(SocketShutdown.Both); } catch { }
        }
        _client.Close();
      }
    }
    catch { }
    finally
    {
      _client = null;
      _connectResult = null;
      _connected = false;
      _helloSent = false;
      Log($"[VaMBridgeCamera] [{name}] Cleanup complete");
    }
  }
}
