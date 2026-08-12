(function () {
    const STROKE_PAD = 4;

    function showSavingOverlay(message) {
        const overlay = document.getElementById("loading-overlay");
        if (!overlay) {
            return;
        }
        const label = overlay.querySelector("[data-saving-label]");
        if (label && message) {
            label.textContent = message;
        }
        overlay.classList.add("is-visible");
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("issuance-saving");
    }

    function hideSavingOverlay() {
        const overlay = document.getElementById("loading-overlay");
        if (!overlay) {
            return;
        }
        overlay.classList.remove("is-visible");
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("issuance-saving");
    }

    window.showSavingOverlay = showSavingOverlay;
    window.hideSavingOverlay = hideSavingOverlay;

    function bindIssuanceForms() {
        document.querySelectorAll("form.js-issuance-form").forEach(function (form) {
            if (form.dataset.issuanceBound === "1") {
                return;
            }
            form.dataset.issuanceBound = "1";

            const signatureInput = form.querySelector("#signature");
            const photoInput = form.querySelector("#photo");
            const submitBtn = form.querySelector('button[type="submit"]');
            const savingMessage = form.dataset.savingMessage || "Сохранение данных…";

            form.addEventListener("submit", function (event) {
                if (form.dataset.issuanceSubmitting === "1") {
                    return;
                }
                event.preventDefault();

                if (!form.checkValidity()) {
                    form.reportValidity();
                    return;
                }

                if (signatureInput) {
                    const signatureValue = (signatureInput.value || "").trim();
                    if (!signatureValue.startsWith("data:image/")) {
                        alert("Пожалуйста, добавьте подпись перед сохранением.");
                        return;
                    }
                }

                if (photoInput && !(photoInput.value || "").trim()) {
                    photoInput.disabled = true;
                }

                form.dataset.issuanceSubmitting = "1";
                showSavingOverlay(savingMessage);
                if (submitBtn) {
                    submitBtn.disabled = true;
                }

                requestAnimationFrame(function () {
                    form.submit();
                });
            });
        });
    }

    if (typeof Webcam !== "undefined" && document.getElementById("cameraModal")) {
        Webcam.set({
            width: 320,
            height: 240,
            image_format: "jpeg",
            jpeg_quality: 85
        });

        $("#cameraModal").on("shown.bs.modal", function () {
            Webcam.attach("#camera");
        });

        $("#cameraModal").on("hidden.bs.modal", function () {
            Webcam.reset();
        });
    }

    window.takeSnapshot = function takeSnapshot() {
        const photoInput = document.getElementById("photo");
        if (!photoInput || typeof Webcam === "undefined") {
            return;
        }
        Webcam.snap(function (dataUri) {
            photoInput.disabled = false;
            photoInput.value = dataUri;
            const preview = document.getElementById("profile-preview");
            if (preview) {
                preview.src = dataUri;
            }
            $("#cameraModal").modal("hide");
        });
    };

    if (typeof $ !== "undefined" && $("#imageModal").length) {
        $("#imageModal").on("show.bs.modal", function (event) {
            var button = $(event.relatedTarget);
            var imagePath = button.data("image");

            var modal = $(this);
            var imgElement = modal.find("#imageModalContent");
            var noImageText = modal.find("#noImageText");

            if (imagePath) {
                imgElement.attr("src", imagePath).show();
                noImageText.hide();
            } else {
                imgElement.hide();
                noImageText.show();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindIssuanceForms();

        const canvas = document.getElementById("signatureCanvas");
        const screen = document.getElementById("signatureScreen");
        const openSignature = document.getElementById("openSignature");
        const previewImg = document.getElementById("signature-preview");
        const signatureInput = document.getElementById("signature");
        const clearBtn = document.getElementById("clearSignature");
        const cancelBtn = document.getElementById("cancelSignature");
        const saveBtn = document.getElementById("saveSignature");

        if (!canvas || !screen || !openSignature || !previewImg || !signatureInput) {
            return;
        }

        const ctx = canvas.getContext("2d", {alpha: true});
        let drawing = false;
        let isSigned = false;
        let bounds = null;

        function resetBounds() {
            bounds = null;
        }

        function extendBounds(x, y) {
            const minX = x - STROKE_PAD;
            const minY = y - STROKE_PAD;
            const maxX = x + STROKE_PAD;
            const maxY = y + STROKE_PAD;

            if (!bounds) {
                bounds = {minX: minX, minY: minY, maxX: maxX, maxY: maxY};
                return;
            }

            bounds.minX = Math.min(bounds.minX, minX);
            bounds.minY = Math.min(bounds.minY, minY);
            bounds.maxX = Math.max(bounds.maxX, maxX);
            bounds.maxY = Math.max(bounds.maxY, maxY);
        }

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            canvas.style.width = "";
            canvas.style.height = "";
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            resetBounds();
        }

        function getPos(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            if (e.touches) {
                return {
                    x: (e.touches[0].clientX - rect.left) * scaleX,
                    y: (e.touches[0].clientY - rect.top) * scaleY
                };
            }
            return {
                x: (e.clientX - rect.left) * scaleX,
                y: (e.clientY - rect.top) * scaleY
            };
        }

        function exportSignatureCanvas() {
            if (!bounds) {
                return null;
            }

            const left = Math.max(0, Math.floor(bounds.minX));
            const top = Math.max(0, Math.floor(bounds.minY));
            const right = Math.min(canvas.width, Math.ceil(bounds.maxX));
            const bottom = Math.min(canvas.height, Math.ceil(bounds.maxY));
            const width = right - left;
            const height = bottom - top;

            if (width <= 0 || height <= 0) {
                return null;
            }

            const trimmed = document.createElement("canvas");
            trimmed.width = width;
            trimmed.height = height;
            trimmed.getContext("2d").drawImage(canvas, left, top, width, height, 0, 0, width, height);
            return trimmed;
        }

        function exportSignatureDataUrl() {
            const trimmed = exportSignatureCanvas();
            if (!trimmed) {
                return null;
            }

            return trimmed.toDataURL("image/png");
        }

        function markSignatureSaved(dataURL) {
            signatureInput.disabled = false;
            signatureInput.value = dataURL;
            previewImg.src = dataURL;
            previewImg.alt = "Подпись";
            previewImg.dataset.hasSignature = "1";

            const previewBox = previewImg.closest(".signature-preview-container");
            if (previewBox) {
                previewBox.classList.remove("stepper-spec__signature-empty", "stepper-archive__signature-empty");
                const hint = previewBox.querySelector("[data-signature-hint]");
                if (hint) {
                    hint.hidden = true;
                }
            }
        }

        function startDraw(e) {
            e.preventDefault();
            const pos = getPos(e);
            drawing = true;
            isSigned = true;
            extendBounds(pos.x, pos.y);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
        }

        function draw(e) {
            if (!drawing) {
                return;
            }
            e.preventDefault();
            const pos = getPos(e);
            extendBounds(pos.x, pos.y);
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = "blue";
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        }

        function stopDraw(e) {
            e.preventDefault();
            drawing = false;
            ctx.closePath();
        }

        canvas.addEventListener("mousedown", startDraw);
        canvas.addEventListener("mousemove", draw);
        canvas.addEventListener("mouseup", stopDraw);
        canvas.addEventListener("mouseout", stopDraw);

        canvas.addEventListener("touchstart", startDraw, {passive: false});
        canvas.addEventListener("touchmove", draw, {passive: false});
        canvas.addEventListener("touchend", stopDraw);

        openSignature.addEventListener("click", function (event) {
            event.preventDefault();
            screen.style.display = "block";
            resizeCanvas();
            isSigned = false;
        });

        if (clearBtn) {
            clearBtn.onclick = function () {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                isSigned = false;
                resetBounds();
            };
        }

        if (cancelBtn) {
            cancelBtn.onclick = function () {
                screen.style.display = "none";
            };
        }

        if (saveBtn) {
            saveBtn.onclick = function () {
                if (!isSigned || !bounds) {
                    alert("Пожалуйста, нарисуйте подпись.");
                    return;
                }

                const dataUrl = exportSignatureDataUrl();
                if (!dataUrl) {
                    alert("Подпись пуста.");
                    return;
                }

                markSignatureSaved(dataUrl);
                screen.style.display = "none";
            };
        }

        window.addEventListener("resize", function () {
            if (screen.style.display === "block") {
                resizeCanvas();
                isSigned = false;
            }
        });
    });
})();
