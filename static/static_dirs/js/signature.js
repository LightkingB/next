const canvas = document.getElementById("signature-pad");
const ctx = canvas.getContext("2d");
const hiddenInput = document.getElementById("photo");

let drawing = false;
let points = [];


ctx.lineWidth = 2.2;
ctx.lineCap = "round";
ctx.lineJoin = "round";
ctx.strokeStyle = "#0051ff";

canvas.addEventListener("mousedown", e => {
    drawing = true;
    points = [{x: e.offsetX, y: e.offsetY}];
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
});

canvas.addEventListener("mousemove", e => {
    if (!drawing) return;
    const point = {x: e.offsetX, y: e.offsetY};
    points.push(point);
    drawSmoothLine();
});

canvas.addEventListener("mouseup", () => {
    drawing = false;
    saveSignature();
});

canvas.addEventListener("mouseleave", () => {
    drawing = false;
});

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