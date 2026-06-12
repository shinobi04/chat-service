import os
import base64
import logging
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
from fastapi import UploadFile, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported MIME type groups
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PDF_TYPES = {"application/pdf"}
AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/x-wav",
               "audio/flac", "audio/x-m4a", "audio/webm", "audio/aac"}
TEXT_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}

# Text file extensions as fallback when MIME type is generic
TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}

# Lazy-loaded Whisper model (loaded on first audio request, then cached)
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the Whisper model so it doesn't consume memory until needed."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading faster-whisper '%s' model...", settings.WHISPER_MODEL_SIZE)
        _whisper_model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8"
        )
        logger.info("Whisper model loaded successfully.")
    return _whisper_model


@dataclass
class ProcessedFile:
    """Result of processing an uploaded file."""
    images_base64: list[str] = field(default_factory=list)   # For images / PDF pages
    extracted_text: Optional[str] = None                      # For audio / markdown / text
    original_filename: Optional[str] = None


def _detect_file_type(file: UploadFile) -> str:
    """Categorize the uploaded file into: image, pdf, audio, text, or unknown."""
    content_type = (file.content_type or "").lower()
    extension = os.path.splitext(file.filename or "")[-1].lower()

    if content_type in IMAGE_TYPES:
        return "image"
    if content_type in PDF_TYPES or extension == ".pdf":
        return "pdf"
    if content_type in AUDIO_TYPES:
        return "audio"
    if content_type in TEXT_TYPES or extension in TEXT_EXTENSIONS:
        return "text"
    return "unknown"


async def process_file(file: UploadFile) -> ProcessedFile:
    """
    Reads the uploaded file, detects its type, and processes it:
      - Image  → base64 encode
      - PDF    → render each page to PNG → base64 encode (up to MAX_PDF_PAGES)
      - Audio  → transcribe with faster-whisper → extracted_text
      - Text   → read as UTF-8 → extracted_text
    """
    # --- Size check ---
    file_bytes = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE_MB}MB."
        )

    file_type = _detect_file_type(file)
    result = ProcessedFile(original_filename=file.filename)

    if file_type == "image":
        result.images_base64 = [base64.b64encode(file_bytes).decode("utf-8")]

    elif file_type == "pdf":
        result.images_base64 = _process_pdf(file_bytes)

    elif file_type == "audio":
        result.extracted_text = _process_audio(file_bytes, file.filename or "audio.wav")

    elif file_type == "text":
        try:
            result.extracted_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Text file is not valid UTF-8.")

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Supported: images (jpeg/png/webp/gif), PDF, audio (mp3/wav/ogg/m4a/flac), "
                "and text/markdown files."
            )
        )

    return result


def _process_pdf(file_bytes: bytes) -> list[str]:
    """Convert each PDF page to a PNG image and return as base64 strings."""
    images_b64: list[str] = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = min(len(doc), settings.MAX_PDF_PAGES)

        if len(doc) > settings.MAX_PDF_PAGES:
            logger.warning(
                "PDF has %d pages, processing only the first %d.",
                len(doc), settings.MAX_PDF_PAGES
            )

        for page_num in range(page_count):
            page = doc[page_num]
            # Render at 2x resolution for readability
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            png_bytes = pix.tobytes("png")
            images_b64.append(base64.b64encode(png_bytes).decode("utf-8"))

        doc.close()
    except Exception as e:
        logger.exception("Failed to process PDF")
        raise HTTPException(status_code=400, detail=f"Failed to process PDF: {e}")

    return images_b64


def _process_audio(file_bytes: bytes, filename: str) -> str:
    """Transcribe audio using faster-whisper and return the transcript text."""
    # faster-whisper needs a file path, so write to a temp file
    suffix = os.path.splitext(filename)[-1] or ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        model = _get_whisper_model()
        segments, info = model.transcribe(tmp_path, beam_size=5)

        transcript_parts = [segment.text for segment in segments]
        transcript = " ".join(transcript_parts).strip()

        logger.info(
            "Audio transcribed: language=%s, probability=%.2f, duration=%.1fs, chars=%d",
            info.language, info.language_probability, info.duration, len(transcript)
        )

        if not transcript:
            return "[No speech detected in audio file]"

        return f"[Transcribed audio from '{filename}']\n{transcript}"

    except Exception as e:
        logger.exception("Failed to transcribe audio")
        raise HTTPException(status_code=400, detail=f"Failed to transcribe audio: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
