// -----------------------------------------------------------------------------
// Project: VaMBridgeCamera
// Component: SocketUtils.cs (Virt-a-Mate Plugin - Camera Bridge Utilities)
// Copyright (c) 2025 MaryJaneVaM
// Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike
// 4.0 International License (CC BY-NC-SA 4.0).
//
// You may share and adapt this file for non-commercial purposes, provided that
// you give appropriate credit and distribute your contributions under the same
// license. Full license: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// Path: VaMBridgeCamera/SocketUtils.cs
// -----------------------------------------------------------------------------

// Short script description.
// Minimal TCP socket utilities for framed JSON communication between VaM and
// external bridge servers. Provides send/receive helpers for length-prefixed
// UTF-8 JSON messages.

using System;
using System.Net.Sockets;
using System.Text;

public static class SocketUtils
{
  /// <summary>
  /// Sends a framed JSON string over the socket.
  /// Frame format: [4-byte length][UTF-8 payload].
  /// </summary>
  public static void SendFrame(Socket client, string json)
  {
    if (client == null || !client.Connected) return;

    byte[] payload = Encoding.UTF8.GetBytes(json);
    int len = payload.Length;

    byte[] frame = new byte[4 + len];
    frame[0] = (byte)(len & 0xFF);
    frame[1] = (byte)((len >> 8) & 0xFF);
    frame[2] = (byte)((len >> 16) & 0xFF);
    frame[3] = (byte)((len >> 24) & 0xFF);
    Buffer.BlockCopy(payload, 0, frame, 4, len);

    client.Send(frame, SocketFlags.None);
  }

  /// <summary>
  /// Receives a framed JSON string from the socket.
  /// Returns null if insufficient data is available.
  /// </summary>
  public static string ReceiveFrame(Socket client, byte[] buffer)
  {
    if (client == null || !client.Connected || client.Available < 4) return null;

    byte[] lenBuf = new byte[4];
    int r = client.Receive(lenBuf, 0, 4, SocketFlags.None);
    if (r != 4) return null;

    int length = lenBuf[0] | (lenBuf[1] << 8) | (lenBuf[2] << 16) | (lenBuf[3] << 24);
    if (length <= 0 || length > buffer.Length) return null;

    int read = 0;
    while (read < length)
    {
      int chunk = client.Receive(buffer, read, length - read, SocketFlags.None);
      if (chunk <= 0) break;
      read += chunk;
    }

    if (read != length) return null;

    return Encoding.UTF8.GetString(buffer, 0, length);
  }

  /// <summary>
  /// Safely closes and disposes the socket.
  /// </summary>
  public static void CloseSocket(Socket client)
  {
    if (client == null) return;
    try
    {
      if (client.Connected)
      {
        try { client.Shutdown(SocketShutdown.Both); } catch { }
        client.Close();
      }
    }
    catch { }
  }
}
