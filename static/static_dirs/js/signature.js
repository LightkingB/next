const canvas = document.getElementById("signature-pad");
const ctx = canvas.getContext("2d");
const hiddenInput = document.getElementById("photo");

let drawing = false;
let points = [];


ctx.lineWidth = 2.2;
ctx.lineCap = "round";
ctx.lineJoin = "round";
ctx.strokeStyle = "#0051ff";

function getCanvasPos(e) {
    if (e.touches && e.touches.length > 0) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.touches[0].clientX - rect.left,
            y: e.touches[0].clientY - rect.top
        };
    } else {
        return {x: e.offsetX, y: e.offsetY};
    }
}

function startDraw(e) {
    e.preventDefault();
    drawing = true;
    const pos = getCanvasPos(e);
    points = [pos];
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
}

function draw(e) {
    if (!drawing) return;
    e.preventDefault();
    const pos = getCanvasPos(e);
    points.push(pos);
    drawSmoothLine();
}

function stopDraw() {
    drawing = false;
    saveSignature();
}

function drawSmoothLine() {
    if (points.length < 3) {
        const b = points[0];
        ctx.beginPath();
        ctx.arc(b.x, b.y, ctx.lineWidth / 2, 0, Math.PI * 2, true);
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fill();
        ctx.closePath();
        return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);

    for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }

    ctx.stroke();
}

function saveSignature() {
    hiddenInput.value = canvas.toDataURL("image/png");
}

function clearSignature() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    hiddenInput.value = "";
    points = [];
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

