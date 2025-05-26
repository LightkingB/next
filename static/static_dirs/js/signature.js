const canvas = document.getElementById("signature-pad");
const ctx = canvas.getContext("2d");
const hiddenInput = document.getElementById("photo");

let drawing = false;
let lastPoint = null;

ctx.lineWidth = 2.2;
ctx.lineCap = "round";
ctx.lineJoin = "round";
ctx.strokeStyle = "#0051ff";

function getCanvasPos(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.touches && e.touches.length > 0) {
        return {
            x: e.touches[0].clientX - rect.left,
            y: e.touches[0].clientY - rect.top
        };
    } else {
        return {
            x: e.offsetX,
            y: e.offsetY
        };
    }
}

function startDraw(e) {
    e.preventDefault();
    drawing = true;
    lastPoint = getCanvasPos(e);
}

function draw(e) {
    if (!drawing) return;
    e.preventDefault();
    const currentPoint = getCanvasPos(e);

    // Плавная линия — кривая Безье через контрольную точку
    ctx.beginPath();
    ctx.moveTo(lastPoint.x, lastPoint.y);
    ctx.lineTo(currentPoint.x, currentPoint.y);
    ctx.stroke();

    lastPoint = currentPoint;
}

function stopDraw() {
    if (drawing) {
        drawing = false;
        saveSignature();
    }
}

function saveSignature() {
    hiddenInput.value = canvas.toDataURL("image/png");
}

function clearSignature() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    hiddenInput.value = "";
    lastPoint = null;
}

// Мышь
canvas.addEventListener("mousedown", startDraw);
canvas.addEventListener("mousemove", draw);
canvas.addEventListener("mouseup", stopDraw);
canvas.addEventListener("mouseleave", stopDraw);

// Touch
canvas.addEventListener("touchstart", startDraw, {passive: false});
canvas.addEventListener("touchmove", draw, {passive: false});
canvas.addEventListener("touchend", stopDraw);