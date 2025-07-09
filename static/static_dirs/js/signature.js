Webcam.set({
    width: 360,
    height: 290,
    image_format: 'jpeg',
    jpeg_quality: 90
});

$('#cameraModal').on('shown.bs.modal', function () {
    Webcam.attach('#camera');
});

$('#cameraModal').on('hidden.bs.modal', function () {
    Webcam.reset();
});

function takeSnapshot() {
    Webcam.snap(function (dataUri) {
        document.getElementById('photo').value = dataUri;
        const preview = document.getElementById('profile-preview');
        if (preview) {
            preview.src = dataUri;
        }
        $('#cameraModal').modal('hide');
    });
}


$('#imageModal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget);
    var imagePath = button.data('image');

    var modal = $(this);
    var imgElement = modal.find('#imageModalContent');
    var noImageText = modal.find('#noImageText');

    if (imagePath) {
        imgElement.attr('src', imagePath).show();
        noImageText.hide();
    } else {
        imgElement.hide();
        noImageText.show();
    }
});
document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("signatureCanvas");
    const ctx = canvas.getContext("2d");
    const screen = document.getElementById("signatureScreen");
    const previewImg = document.getElementById("signature-preview");

    let drawing = false;
    let isSigned = false;

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        return e.touches ? {
            x: e.touches[0].clientX - rect.left,
            y: e.touches[0].clientY - rect.top
        } : {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    function startDraw(e) {
        e.preventDefault();
        const pos = getPos(e);
        drawing = true;
        isSigned = true;
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }

    function draw(e) {
        if (!drawing) return;
        e.preventDefault();
        const pos = getPos(e);
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "blue";
        ctx.lineCap = "round";
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
    }

    function stopDraw(e) {
        e.preventDefault();
        drawing = false;
        ctx.closePath();
    }

    function trimCanvas(canvas) {
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        const imageData = ctx.getImageData(0, 0, width, height);
        const data = imageData.data;

        let top = null, bottom = null, left = null, right = null;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const alpha = data[(y * width + x) * 4 + 3];
                if (alpha > 0) {
                    if (top === null) top = y;
                    bottom = y;
                    if (left === null || x < left) left = x;
                    if (right === null || x > right) right = x;
                }
            }
        }

        if (top === null) return null;

        const trimmedWidth = right - left + 1;
        const trimmedHeight = bottom - top + 1;
        const trimmedCanvas = document.createElement("canvas");
        trimmedCanvas.width = trimmedWidth;
        trimmedCanvas.height = trimmedHeight;
        const trimmedCtx = trimmedCanvas.getContext("2d");

        trimmedCtx.clearRect(0, 0, trimmedWidth, trimmedHeight);
        trimmedCtx.drawImage(canvas, left, top, trimmedWidth, trimmedHeight, 0, 0, trimmedWidth, trimmedHeight);

        return trimmedCanvas;
    }

// События canvas
    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", stopDraw);
    canvas.addEventListener("mouseout", stopDraw);

    canvas.addEventListener("touchstart", startDraw, {passive: false});
    canvas.addEventListener("touchmove", draw, {passive: false});
    canvas.addEventListener("touchend", stopDraw);

// Открытие
    document.getElementById("openSignature").onclick = () => {
        screen.style.display = "block";
        resizeCanvas();
        isSigned = false;
    };

// Очистка
    document.getElementById("clearSignature").onclick = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        isSigned = false;
    };

// Отмена
    document.getElementById("cancelSignature").onclick = () => {
        screen.style.display = "none";
    };

// Сохранение
    document.getElementById("saveSignature").onclick = () => {
        if (!isSigned) return alert("Пожалуйста, нарисуйте подпись.");
        const trimmed = trimCanvas(canvas);
        if (!trimmed) return alert("Подпись пуста.");
        const dataURL = trimmed.toDataURL("image/png");

        document.getElementById("signature").value = dataURL;
        previewImg.src = dataURL;
        screen.style.display = "none";
    };

// Адаптация к окну
    window.addEventListener("resize", () => {
        if (screen.style.display === "block") resizeCanvas();
    });
});