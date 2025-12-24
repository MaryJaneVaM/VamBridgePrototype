let loadedImageBlob = null;

const poseImage = document.getElementById("poseImage");
const poseImageContainer = document.getElementById("poseImageContainer");
const responseBox = document.getElementById("responseBoxPose");

document.getElementById("btnOpenImage").addEventListener("click", openImageDialog);
document.getElementById("btnHolistics").addEventListener("click", () => sendToEndpoint("holistic"));
document.getElementById("btnPose").addEventListener("click", () => sendToEndpoint("pose"));
document.getElementById("btnHands").addEventListener("click", () => sendToEndpoint("hands"));

document.getElementById("btnCopyResponse").addEventListener("click", () => {
  const text = responseBox.textContent;
  navigator.clipboard.writeText(text)
    .then(() => console.log("Copied response to clipboard"))
    .catch(err => console.error("Copy failed:", err));
});

let analysisImageWidth = null;
let analysisImageHeight = null;

function openImageDialog() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";

  input.onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    loadedImageBlob = file;

    const url = URL.createObjectURL(file);
    poseImage.src = url;

    responseBox.textContent = "Image loaded. Ready for processing.";
  };

  input.click();
}

poseImage.onload = () => {
  const canvas = document.getElementById("poseCanvas");
  const rect = poseImageContainer.getBoundingClientRect();

  canvas.width = rect.width;
  canvas.height = rect.height;

  canvas.style.width = rect.width + "px";
  canvas.style.height = rect.height + "px";

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
};

async function sendToEndpoint(type) {
  if (!loadedImageBlob) {
    responseBox.textContent = "Please load an image first.";
    return;
  }

  const endpoint = {
    holistic: "http://localhost:5005/detect/holistic",
    pose: "http://localhost:5005/detect/pose",
    hands: "http://localhost:5005/detect/hands"
  }[type];

  responseBox.textContent = `Sending image to ${type} endpoint...`;

  try {
    const resizedBlob = await resizeImage(loadedImageBlob, 512);

    const response = await fetch(endpoint, {
      method: "POST",
      body: resizedBlob
    });

    const data = await response.json();

    responseBox.textContent = JSON.stringify(data, null, 2);

    if (data.meta && data.meta.image) {
      analysisImageWidth = data.meta.image.width;
      analysisImageHeight = data.meta.image.height;
    } else {
      analysisImageWidth = null;
      analysisImageHeight = null;
    }

    drawOverlay(data);

  } catch (err) {
    responseBox.textContent = "Error: " + err;
  }
}

function resizeImage(file, maxWidth) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      let width = img.width;
      let height = img.height;

      if (width > maxWidth) {
        height = (maxWidth / width) * height;
        width = maxWidth;
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          resolve(blob);
          URL.revokeObjectURL(url);
        },
        "image/jpeg",
        0.9
      );
    };

    img.onerror = reject;
    img.src = url;
  });
}

function getDisplayedImageRect() {
  const container = poseImageContainer.getBoundingClientRect();

  const naturalW = poseImage.naturalWidth;
  const naturalH = poseImage.naturalHeight;

  if (!naturalW || !naturalH) {
    return null;
  }

  const scale = Math.min(
    container.width / naturalW,
    container.height / naturalH
  );

  const displayW = naturalW * scale;
  const displayH = naturalH * scale;

  const offsetX = (container.width - displayW) / 2;
  const offsetY = (container.height - displayH) / 2;

  return { displayW, displayH, offsetX, offsetY };
}

function drawOverlay(data) {
  const canvas = document.getElementById("poseCanvas");
  const ctx = canvas.getContext("2d");

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!data) return;

  const rect = getDisplayedImageRect();
  if (!rect) return;

  const { displayW, displayH, offsetX, offsetY } = rect;

  const srcW = analysisImageWidth || poseImage.naturalWidth;
  const srcH = analysisImageHeight || poseImage.naturalHeight;

  if (!srcW || !srcH) return;

  const factorX = displayW / srcW;
  const factorY = displayH / srcH;

  const mapPoint = (p) => ({
    x: offsetX + p.x_px * factorX,
    y: offsetY + p.y_px * factorY
  });

  if (data.pose && data.pose.landmarks) {
    drawPose(ctx, data.pose.landmarks, mapPoint, "lime");
  }

  if (data.hand_left && data.hand_left.landmarks) {
    drawHand(ctx, data.hand_left.landmarks, mapPoint, "cyan");
  }

  if (data.hand_right && data.hand_right.landmarks) {
    drawHand(ctx, data.hand_right.landmarks, mapPoint, "red");
  }
}

const POSE_CONNECTIONS = [
  [11, 13], [13, 15],
  [12, 14], [14, 16],
  [11, 12],
  [23, 24],
  [11, 23], [12, 24],
  [23, 25], [25, 27],
  [24, 26], [26, 28],
  [27, 29], [29, 31],
  [28, 30], [30, 32]
];

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20]
];

function drawPose(ctx, landmarks, mapPoint, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;

  for (const [a, b] of POSE_CONNECTIONS) {
    const p1 = landmarks[a];
    const p2 = landmarks[b];
    if (!p1 || !p2) continue;

    const s1 = mapPoint(p1);
    const s2 = mapPoint(p2);

    ctx.beginPath();
    ctx.moveTo(s1.x, s1.y);
    ctx.lineTo(s2.x, s2.y);
    ctx.stroke();
  }

  for (const p of landmarks) {
    const s = mapPoint(p);
    drawPoint(ctx, s.x, s.y, color);
  }
}

function drawHand(ctx, landmarks, mapPoint, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;

  for (const [a, b] of HAND_CONNECTIONS) {
    const p1 = landmarks[a];
    const p2 = landmarks[b];
    if (!p1 || !p2) continue;

    const s1 = mapPoint(p1);
    const s2 = mapPoint(p2);

    ctx.beginPath();
    ctx.moveTo(s1.x, s1.y);
    ctx.lineTo(s2.x, s2.y);
    ctx.stroke();
  }

  for (const p of landmarks) {
    const s = mapPoint(p);
    drawPoint(ctx, s.x, s.y, color);
  }
}

function drawPoint(ctx, x, y, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fill();
}
