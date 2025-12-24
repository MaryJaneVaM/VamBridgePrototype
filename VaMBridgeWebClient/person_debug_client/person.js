(() => {
  let wsPerson;
  const respPerson = document.getElementById("responseBoxPerson");
  const payloadBox = document.getElementById("payloadBox");

  function logResponse(msg) {
    respPerson.textContent += "\n" + msg;
    respPerson.scrollTop = respPerson.scrollHeight;
  }

  function clearResponse() {
    respPerson.textContent = "";
  }

  function connect() {
    wsPerson = new WebSocket("ws://127.0.0.1:5102");

    wsPerson.onopen = () => {
      logResponse("[WS] Connected");

      const hello = {
        cmd: "hello",
        id: "WebPersonClient",
        name: "WebPersonClient"
      };

      wsPerson.send(JSON.stringify(hello));
      logResponse("[WS] Sent hello");
      logResponse("[WS] Payload:\n" + JSON.stringify(hello, null, 2));
    };

    wsPerson.onclose = () => logResponse("[WS] Disconnected");
    wsPerson.onerror = (err) =>
      logResponse("[WS] Error: " + (err.message || err));

    wsPerson.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // ⭐ Ignore messages meant for other clients (Camera, etc.)
        if (data.id && data.id !== "WebPersonClient" && data.id !== "Person") {
          return;
        }

        logResponse("[WS] Received:\n" + JSON.stringify(data, null, 2));
      } catch (e) {
        logResponse("[WS] Bad message: " + event.data);
      }
    };
  }

  function sendRequest(cmd) {
    if (!wsPerson || wsPerson.readyState !== WebSocket.OPEN) {
      logResponse("[WS] Not connected");
      return;
    }

    clearResponse();

    const msg = {
      cmd,
      id: "Person",
      name: "Person"
    };

    wsPerson.send(JSON.stringify(msg));
    logResponse("[WS] Sent command: " + cmd);
    logResponse("[WS] Payload:\n" + JSON.stringify(msg, null, 2));
  }

  function sendPayload() {
    if (!wsPerson || wsPerson.readyState !== WebSocket.OPEN) {
      logResponse("[WS] Not connected");
      return;
    }

    clearResponse();

    try {
      const parsed = JSON.parse(payloadBox.value);
      wsPerson.send(JSON.stringify(parsed));
      logResponse("[WS] Sent custom payload");
      logResponse("[WS] Payload:\n" + JSON.stringify(parsed, null, 2));
    } catch {
      logResponse("[WS] Invalid JSON in payload box");
    }
  }

  function fillControllerPayload() {
    payloadBox.value = `{
  "cmd": "set_controllers",
  "id": "Person",
  "name": "Person",
  "data": [
    {
      "id": "control",
      "position": { "x": "0", "y": "1", "z": "0" }
      "rotationEuler": { "x": "0", "y": "45", "z": "0" }
    }
  ]
}`;
  }

  function fillMorphPayload() {
    payloadBox.value = `{
  "cmd": "set_morphs",
  "id": "Person",
  "name": "Person",
  "data": [
    { "name": "morph: AV_LargerVagina", "value": "0.8" }
  ]
}`;
  }

  window.addEventListener("load", () => {
    connect();

    document.getElementById("btnReadControllers")
      .addEventListener("click", () => sendRequest("read_all_controllers"));

    document.getElementById("btnReadMorphs")
      .addEventListener("click", () => sendRequest("read_all_morphs"));

    document.getElementById("btnSendPayload")
      .addEventListener("click", sendPayload);

    document.getElementById("btnControllerPayload")
      .addEventListener("click", fillControllerPayload);

    document.getElementById("btnMorphPayload")
      .addEventListener("click", fillMorphPayload);
  });
})();
