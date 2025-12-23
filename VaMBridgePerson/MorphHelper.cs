// -----------------------------------------------------------------------------
// Project: VaMBridgePerson
// Component: MorphHelper.cs (Virt-a-Mate Plugin - Person Bridge Utilities)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgePerson/MorphHelper.cs
// -----------------------------------------------------------------------------

// Short script description.
// Utility functions for collecting, applying, and serializing Person morphs.
// Builds JSON envelopes for read/set operations and applies morph values safely.

using UnityEngine;
using System;
using System.Net.Sockets;
using SimpleJSON;

namespace MaryJane
{
  public static class MorphHelper
  {
    /// <summary>
    /// Collects all morphs from the Person atom and sends them as a JSON envelope.
    /// </summary>
    public static void SendAllMorphs(Socket client, Atom atom)
    {
      var geo = atom.GetStorableByID("geometry");
      if (geo == null) return;

      var arr = new JSONArray();
      foreach (var name in geo.GetFloatParamNames())
      {
        var dto = new JSONClass();
        dto["name"] = name;
        dto["value"] = geo.GetFloatParamValue(name).ToString();
        dto["min"] = geo.GetFloatJSONParamMinValue(name).ToString();
        dto["max"] = geo.GetFloatJSONParamMaxValue(name).ToString();
        arr.Add(dto);
      }

      var env = new JSONClass();
      env["cmd"] = "read_all_morphs_result";
      env["id"] = atom.uid;
      env["name"] = atom.name;
      env["data"] = arr;

      SocketUtils.SendFrame(client, env.ToString());
    }

    /// <summary>
    /// Applies morph values from a JSON array to the Person atom.
    /// </summary>
    public static void ApplyMorphs(Atom atom, JSONArray arr)
    {
      var geo = atom.GetStorableByID("geometry");
      if (geo == null) return;

      foreach (JSONNode dto in arr)
      {
        string name = dto["name"];
        float value;
        if (float.TryParse(dto["value"], out value))
        {
          geo.SetFloatParamValue(name, value);
        }
      }
    }

    /// <summary>
    /// Sends back only the morphs that were just applied, as a set_morphs_result envelope.
    /// </summary>
    public static void SendSetMorphsResult(Socket client, Atom atom, JSONArray arr)
    {
      var geo = atom.GetStorableByID("geometry");
      if (geo == null) return;

      var resultArr = new JSONArray();
      foreach (JSONNode dto in arr)
      {
        string name = dto["name"];
        var item = new JSONClass();
        item["name"] = name;
        item["value"] = geo.GetFloatParamValue(name).ToString();
        item["min"] = geo.GetFloatJSONParamMinValue(name).ToString();
        item["max"] = geo.GetFloatJSONParamMaxValue(name).ToString();
        resultArr.Add(item);
      }

      var env = new JSONClass();
      env["cmd"] = "set_morphs_result";
      env["id"] = atom.uid;
      env["name"] = atom.name;
      env["data"] = resultArr;

      SocketUtils.SendFrame(client, env.ToString());
    }
  }
}
