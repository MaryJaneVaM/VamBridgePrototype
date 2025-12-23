// -----------------------------------------------------------------------------
// Project: VaMBridgePerson
// Component: VaMBridgePerson.cs (Virt-a-Mate Plugin - Person Bridge Main Script)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgePerson/VaMBridgePerson.cs
// -----------------------------------------------------------------------------

// Short script description.
// Main entry point for the Person bridge plugin. Handles socket connection,
// handshake, update loop, and dispatching controller/morph commands.

using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using SimpleJSON;

namespace MaryJane
{
  public class VaMBridgePerson : MVRScript
  {
    private const string HOST = "127.0.0.1";
    private const int PORT = 5000;

    private Socket _client;
    private IAsyncResult _connectResult;
    private bool _connected;
    private bool _helloSent;
    private readonly byte[] _recvBuf = new byte[65536];

    // Logging toggle
    private static bool _enableLogs = false;

    // Cached atom name for consistent logging
    private string _atomName = "Unknown";

    private void Log(string message)
    {
      if (_enableLogs)
      {
        SuperController.LogMessage(message);
      }
    }

    private void LogError(string message)
    {
      if (_enableLogs)
      {
        SuperController.LogError(message);
      }
    }

    // Initialization -----------------------------------------------------------
    public override void Init()
    {
      if (containingAtom == null || containingAtom.type != "Person")
      {
        LogError("[VaMBridgePerson] Must be attached to a Person atom.");
        return;
      }

      _atomName = containingAtom.name; // cache name early

      try
      {
        _client = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp) { NoDelay = true };
        _connectResult = _client.BeginConnect(new IPEndPoint(IPAddress.Parse(HOST), PORT), null, null);
      }
      catch (Exception e)
      {
        LogError($"[VaMBridgePerson] [{_atomName}] Init error: {e.Message}");
        Cleanup();
      }
    }

    // Update loop --------------------------------------------------------------
    public void Update()
    {
      try
      {
        CompleteConnectionIfPending();

        if (_connected && !_helloSent)
        {
          SendHello();
          _helloSent = true;
        }

        if (_connected)
        {
          string json = SocketUtils.ReceiveFrame(_client, _recvBuf);
          if (!string.IsNullOrEmpty(json))
          {
            var node = JSON.Parse(json);
            Dispatch(node);
          }
        }
      }
      catch (Exception e)
      {
        LogError($"[VaMBridgePerson] [{_atomName}] Update error: {e.Message}");
        Cleanup();
      }
    }

    // Connection handling ------------------------------------------------------
    private void CompleteConnectionIfPending()
    {
      if (!_connected && _client != null && _connectResult != null &&
          _connectResult.AsyncWaitHandle.WaitOne(0, true))
      {
        _client.EndConnect(_connectResult);
        _connectResult = null;
        _connected = _client.Connected;
        string ident = $"[VaMBridgePerson] [{_atomName}]";
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
      Log($"[VaMBridgePerson] [{_atomName}] Sent hello");
    }

    // Command dispatch ---------------------------------------------------------
    private void Dispatch(JSONNode node)
    {
      string cmd = node["cmd"];
      switch (cmd)
      {
        case "read_all_controllers":
          ControllerHelper.SendAllControllers(_client, containingAtom);
          break;

        case "set_controllers":
          ControllerHelper.ApplyControllers(containingAtom, node["data"].AsArray);
          ControllerHelper.SendSetControllersResult(_client, containingAtom, node["data"].AsArray);
          break;

        case "read_all_morphs":
          MorphHelper.SendAllMorphs(_client, containingAtom);
          break;

        case "set_morphs":
          MorphHelper.ApplyMorphs(containingAtom, node["data"].AsArray);
          MorphHelper.SendSetMorphsResult(_client, containingAtom, node["data"].AsArray);
          break;

        case "acknowledge":
          Log($"[VaMBridgePerson] [{_atomName}] Handshake acknowledged by server");
          break;

        default:
          Log($"[VaMBridgePerson] [{_atomName}] Unknown command: {cmd}");
          break;
      }
    }

    // Cleanup ------------------------------------------------------------------
    private void Cleanup()
    {
      string name = _atomName; // use cached name
      try { SocketUtils.CloseSocket(_client); } catch { }
      _client = null;
      _connectResult = null;
      _connected = false;
      _helloSent = false;
      Log($"[VaMBridgePerson] [{name}] Cleanup complete");
    }
  }
}
