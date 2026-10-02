"""
Сжатие PDF через Ghostscript.

Алгоритм (от безопасного к более сильному, останавливаемся, как только файл достаточно мал):
  1. Без потерь: пересборка PDF — сжатие потоков, подмножества шрифтов, удаление
     дублирующихся изображений. JPEG-картинки переносятся как есть, разрешение не трогается.
  2. Если файл всё ещё больше TARGET_SIZE — страницы приводятся к A4 (сканы с телефона
     часто вставлены как страницы метрового размера), изображения уменьшаются до 200 dpi.
  3. Если всё ещё больше — 150 dpi. Ниже не опускаемся: при 150 dpi текст
     и рукописные пометки остаются читабельными.

Из всех вариантов сохраняется самый маленький; если сжатие ничего не дало
(или Ghostscript недоступен/упал) — возвращается исходный файл.
"""
import logging
import os
import shutil
import subprocess
import tempfile

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

TARGET_SIZE = 1 * 1024 * 1024
GS_TIMEOUT = 90

_COMMON_ARGS = [
    "-sDEVICE=pdfwrite",
    "-dCompatibilityLevel=1.5",
    "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
    "-dDetectDuplicateImages=true",
    "-dCompressFonts=true",
    "-dSubsetFonts=true",
]

_LOSSLESS_ARGS = [
    "-dPassThroughJPEGImages=true",
    "-dDownsampleColorImages=false",
    "-dDownsampleGrayImages=false",
    "-dDownsampleMonoImages=false",
    "-dAutoFilterColorImages=false",
    "-dAutoFilterGrayImages=false",
    "-dColorImageFilter=/FlateEncode",
    "-dGrayImageFilter=/FlateEncode",
]


def _downsample_args(dpi, jpeg_quality):
    return [
        "-sPAPERSIZE=a4", "-dFIXEDMEDIA", "-dPDFFitPage",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDownsampleMonoImages=true",
        "-dColorImageDownsampleType=/Bicubic",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi * 2}",
        "-dColorImageDownsampleThreshold=1.0",
        "-dGrayImageDownsampleThreshold=1.0",
        "-dAutoFilterColorImages=false",
        "-dAutoFilterGrayImages=false",
        "-dColorImageFilter=/DCTEncode",
        "-dGrayImageFilter=/DCTEncode",
        f"-dJPEGQ={jpeg_quality}",
    ]


STEPS = [
    ("lossless", _LOSSLESS_ARGS),
    ("200dpi", _downsample_args(200, 85)),
    ("150dpi", _downsample_args(150, 75)),
]


def _run_gs(gs, src, dst, args):
    try:
        subprocess.run([gs, *_COMMON_ARGS, *args, f"-sOutputFile={dst}", src],
                       check=True, timeout=GS_TIMEOUT, capture_output=True)
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("Ghostscript failed (%s): %s", dst, e)
        return None
    if not os.path.exists(dst) or os.path.getsize(dst) < 1024:
        return None
    with open(dst, "rb") as f:
        if f.read(5) != b"%PDF-":
            return None
    return os.path.getsize(dst)


def compress_pdf(uploaded_file, target_size=TARGET_SIZE):
    """Возвращает сжатую копию PDF (ContentFile) или исходный файл, если сжать не удалось."""
    gs = shutil.which("gs")
    if not gs:
        logger.warning("Ghostscript (gs) not found, PDF stored without compression")
        return uploaded_file

    with tempfile.TemporaryDirectory(prefix="pdfcompress_") as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        uploaded_file.seek(0)

        original_size = os.path.getsize(src)
        best_path, best_size, best_step = None, original_size, None

        for index, (name, args) in enumerate(STEPS):
            if index > 0 and best_size <= target_size:
                break
            dst = os.path.join(tmp, f"{name}.pdf")
            size = _run_gs(gs, src, dst, args)
            if size is not None and size < best_size:
                best_path, best_size, best_step = dst, size, name

        if best_path is None:
            logger.info("PDF %s: %d bytes, compression gave no gain", uploaded_file.name, original_size)
            return uploaded_file

        logger.info("PDF %s: %d -> %d bytes (%s)", uploaded_file.name, original_size, best_size, best_step)
        with open(best_path, "rb") as f:
            return ContentFile(f.read(), name=os.path.basename(uploaded_file.name))
