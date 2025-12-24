(() => {
  let wsCamera;
  const respCamera = document.getElementById("responseBoxCamera");
  const imgEl = document.getElementById("cameraImage");

  function logResponse(msg) {
    respCamera.textContent += "\n" + msg;
    respCamera.scrollTop = respCamera.scrollHeight;
  }

  function clearResponses() {
    respCamera.textContent = "";
  }

  function connect() {
    wsCamera = new WebSocket("ws://127.0.0.1:8765");

    wsCamera.onopen = () => {
      logResponse("[WS] Connected");

      const hello = {
        cmd: "hello",
        id: "WebCameraClient",
        name: "WebCameraClient",
      };

      wsCamera.send(JSON.stringify(hello));
      logResponse("[WS] Sent hello");
      logResponse("[WS] Payload:\n" + JSON.stringify(hello, null, 2));
    };

    wsCamera.onclose = () => logResponse("[WS] Disconnected");
    wsCamera.onerror = (err) =>
      logResponse("[WS] Error: " + (err.message || err));

    wsCamera.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // ⭐ Ignore messages meant for other clients
        if (
          data.id &&
          data.id !== "WebCameraClient" &&
          data.id !== "WindowCamera"
        ) {
          return;
        }

        // Handle screenshot
        if (data.cmd === "screenshot_result" && data.data?.imageBase64) {
          imgEl.src = "data:image/png;base64," + data.data.imageBase64;

          const safeData = {
            ...data,
            data: { ...data.data, imageBase64: "[hidden]" },
          };

          logResponse("[WS] Received:\n" + JSON.stringify(safeData, null, 2));
          logResponse("[WS] Camera image updated");
          return;
        }

        // Log everything else
        logResponse("[WS] Received:\n" + JSON.stringify(data, null, 2));

        // Handle read_view_result
        if (
          data.cmd === "read_view_result" &&
          data.data?.position &&
          data.data?.rotationEuler
        ) {
          const pos = data.data.position;
          const rot = data.data.rotationEuler;

          logResponse(
            `[WS] Current View → Pos(${pos.x}, ${pos.y}, ${pos.z}) ` +
            `Euler(${rot.x}, ${rot.y}, ${rot.z})`
          );
        }
      } catch (e) {
        logResponse("[WS] Bad message: " + event.data);
      }
    };
  }

  function sendCameraCommand(cmd) {
    if (!wsCamera || wsCamera.readyState !== WebSocket.OPEN) {
      logResponse("[WS] Not connected");
      return;
    }

    clearResponses();

    const msg = {
      cmd,
      id: "WindowCamera",
      name: "WindowCamera",
    };

    wsCamera.send(JSON.stringify(msg));
    logResponse("[WS] Sent command: " + cmd);
    logResponse("[WS] Payload:\n" + JSON.stringify(msg, null, 2));
  }

  function setCameraView() {
    if (!wsCamera || wsCamera.readyState !== WebSocket.OPEN) {
      logResponse("[WS] Not connected");
      return;
    }

    clearResponses();

    const msg = {
      cmd: "set_view",
      id: "WindowCamera",
      name: "WindowCamera",
      data: {
        id: "control",
        position: {
          x: document.getElementById("camPosX").value,
          y: document.getElementById("camPosY").value,
          z: document.getElementById("camPosZ").value,
        },
        rotationEuler: {
          x: document.getElementById("camRotX").value,
          y: document.getElementById("camRotY").value,
          z: document.getElementById("camRotZ").value,
        },
        imageBase64: "",
      },
    };

    wsCamera.send(JSON.stringify(msg));
    logResponse("[WS] Sent command: set_view");
    logResponse("[WS] Payload:\n" + JSON.stringify(msg, null, 2));
  }

  // ⭐ RESTORED PRESET VIEW FUNCTIONS
  function setFrontView() {
    document.getElementById("camPosX").value = "0";
    document.getElementById("camPosY").value = "0.9";
    document.getElementById("camPosZ").value = "3";
    document.getElementById("camRotX").value = "0";
    document.getElementById("camRotY").value = "180";
    document.getElementById("camRotZ").value = "0";
  }

  function setRightSideView() {
    document.getElementById("camPosX").value = "3";
    document.getElementById("camPosY").value = "0.9";
    document.getElementById("camPosZ").value = "0";
    document.getElementById("camRotX").value = "0";
    document.getElementById("camRotY").value = "270";
    document.getElementById("camRotZ").value = "0";
  }

  function setLeftSideView() {
    document.getElementById("camPosX").value = "-3";
    document.getElementById("camPosY").value = "0.9";
    document.getElementById("camPosZ").value = "0";
    document.getElementById("camRotX").value = "0";
    document.getElementById("camRotY").value = "90";
    document.getElementById("camRotZ").value = "0";
  }

  function setBackView() {
    document.getElementById("camPosX").value = "0";
    document.getElementById("camPosY").value = "0.9";
    document.getElementById("camPosZ").value = "-3";
    document.getElementById("camRotX").value = "0";
    document.getElementById("camRotY").value = "0";
    document.getElementById("camRotZ").value = "0";
  }

  // Expose functions to HTML
  window.sendCameraCommand = sendCameraCommand;
  window.setCameraView = setCameraView;
  window.setFrontView = setFrontView;
  window.setRightSideView = setRightSideView;
  window.setLeftSideView = setLeftSideView;
  window.setBackView = setBackView;

  window.addEventListener("load", connect);
})();
