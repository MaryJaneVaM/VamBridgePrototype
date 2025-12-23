// -----------------------------------------------------------------------------
// Project: VaMBridgePerson
// Component: ControllerHelper.cs (Virt-a-Mate Plugin - Person Bridge Utilities)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgePerson/ControllerHelper.cs
// -----------------------------------------------------------------------------

// Short script description.
// Utility functions for collecting, applying, and serializing Person controllers.
// Builds JSON envelopes for read/set operations and applies transforms safely.

using UnityEngine;
using System;
using System.Net.Sockets;
using SimpleJSON;

namespace MaryJane
{
  public static class ControllerHelper
  {
    /// <summary>
    /// Collects all controllers from the Person atom and sends them as a JSON envelope.
    /// </summary>
    public static void SendAllControllers(Socket client, Atom atom)
    {
      var arr = new JSONArray();
      foreach (var fc in atom.freeControllers)
      {
        var dto = new JSONClass();
        dto["id"] = fc.name;
        dto["name"] = fc.name;

        var pos = fc.transform.localPosition;
        dto["position"]["x"] = pos.x.ToString();
        dto["position"]["y"] = pos.y.ToString();
        dto["position"]["z"] = pos.z.ToString();

        var rot = fc.transform.localRotation;
        dto["rotation"]["x"] = rot.x.ToString();
        dto["rotation"]["y"] = rot.y.ToString();
        dto["rotation"]["z"] = rot.z.ToString();
        dto["rotation"]["w"] = rot.w.ToString();

        var euler = rot.eulerAngles;
        dto["rotationEuler"]["x"] = euler.x.ToString();
        dto["rotationEuler"]["y"] = euler.y.ToString();
        dto["rotationEuler"]["z"] = euler.z.ToString();

        dto["positionState"] = fc.currentPositionState.ToString();
        dto["rotationState"] = fc.currentRotationState.ToString();

        arr.Add(dto);
      }

      var env = new JSONClass();
      env["cmd"] = "read_all_controllers_result";
      env["id"] = atom.uid;
      env["name"] = atom.name;
      env["data"] = arr;

      SocketUtils.SendFrame(client, env.ToString());
    }

    /// <summary>
    /// Applies controller transforms from a JSON array to the Person atom.
    /// </summary>
    public static void ApplyControllers(Atom atom, JSONArray arr)
    {
      foreach (JSONNode dto in arr)
      {
        string id = dto["id"];
        var fc = atom.GetStorableByID(id) as FreeControllerV3;
        if (fc == null) continue;

        float px, py, pz;
        if (float.TryParse(dto["position"]["x"], out px) &&
            float.TryParse(dto["position"]["y"], out py) &&
            float.TryParse(dto["position"]["z"], out pz))
        {
          fc.transform.localPosition = new Vector3(px, py, pz);
        }

        Quaternion rot;

        JSONNode rotNode = dto["rotation"];
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
          fc.transform.localRotation = rot;
          continue;
        }

        JSONNode eulerNode = dto["rotationEuler"];
        bool hasValidEuler =
          eulerNode != null &&
          eulerNode["x"] != null && !string.IsNullOrEmpty(eulerNode["x"].Value) &&
          eulerNode["y"] != null && !string.IsNullOrEmpty(eulerNode["y"].Value) &&
          eulerNode["z"] != null && !string.IsNullOrEmpty(eulerNode["z"].Value);

        if (hasValidEuler)
        {
          float rx = eulerNode["x"].AsFloat;
          float ry = eulerNode["y"].AsFloat;
          float rz = eulerNode["z"].AsFloat;

          fc.transform.localRotation = Quaternion.Euler(rx, ry, rz);
        }
      }
    }

    /// <summary>
    /// Sends back only the controllers that were just applied.
    /// </summary>
    public static void SendSetControllersResult(Socket client, Atom atom, JSONArray arr)
    {
      var resultArr = new JSONArray();
      foreach (JSONNode dto in arr)
      {
        string id = dto["id"];
        var fc = atom.GetStorableByID(id) as FreeControllerV3;
        if (fc == null) continue;

        var item = new JSONClass();
        item["id"] = fc.name;
        item["name"] = fc.name;

        var pos = fc.transform.localPosition;
        item["position"]["x"] = pos.x.ToString();
        item["position"]["y"] = pos.y.ToString();
        item["position"]["z"] = pos.z.ToString();

        var rot = fc.transform.localRotation;
        item["rotation"]["x"] = rot.x.ToString();
        item["rotation"]["y"] = rot.y.ToString();
        item["rotation"]["z"] = rot.z.ToString();
        item["rotation"]["w"] = rot.w.ToString();

        var euler = rot.eulerAngles;
        item["rotationEuler"]["x"] = euler.x.ToString();
        item["rotationEuler"]["y"] = euler.y.ToString();
        item["rotationEuler"]["z"] = euler.z.ToString();

        item["positionState"] = fc.currentPositionState.ToString();
        item["rotationState"] = fc.currentRotationState.ToString();

        resultArr.Add(item);
      }

      var env = new JSONClass();
      env["cmd"] = "set_controllers_result";
      env["id"] = atom.uid;
      env["name"] = atom.name;
      env["data"] = resultArr;

      SocketUtils.SendFrame(client, env.ToString());
    }
  }
}
