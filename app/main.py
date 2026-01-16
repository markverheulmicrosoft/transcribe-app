"""
Main FastAPI application for the Transcription PoC.
"""
import os
import logging
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.services.speech_service import get_transcriber, TranscriptionResult
from app.services.export_service import ExportService
from app.services.audio_converter import ACCEPTED_FORMATS, NATIVE_FORMATS, is_ffmpeg_available

# Lazy import for Azure Speech (may not be configured)
def _get_speech_transcriber():
    from app.services.azure_speech_service import get_speech_transcriber
    return get_speech_transcriber()


def _configure_logging() -> None:
    """Configure logging in a way that plays nicely with uvicorn."""
    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(level)

    # Ensure our app loggers are at least at the configured level.
    logging.getLogger("app").setLevel(level)


_configure_logging()
logger = logging.getLogger("app.main")

# Initialize FastAPI app
app = FastAPI(
    title="Transcribe App",
    description="Proof of Concept for audio transcription with speaker diarization",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for transcription results (in production, use a database)
transcription_store: dict[str, TranscriptionResult] = {}

# Settings
settings = get_settings()

# Ensure upload directory exists
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application page."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return """
    <html>
        <head><title>Transcribe App</title></head>
        <body>
            <h1>Transcribe App</h1>
            <p>Static files not found. Please ensure the static folder exists.</p>
        </body>
    </html>
    """


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config")
async def get_config():
    """Get application configuration (non-sensitive)."""
    return {
        "max_file_size_mb": settings.max_file_size_mb,
        "default_language": settings.default_language,
        "default_engine": settings.transcription_engine,
        "supported_engines": ["openai", "speech"],
        "supported_formats": sorted([ext.lstrip(".") for ext in ACCEPTED_FORMATS]),
        "native_formats": sorted([ext.lstrip(".") for ext in NATIVE_FORMATS]),
        "ffmpeg_available": is_ffmpeg_available(),
        "supported_languages": [
            {"code": "nl", "name": "Nederlands"},
            {"code": "en", "name": "English"},
            {"code": "de", "name": "Deutsch"},
            {"code": "fr", "name": "Français"},
        ]
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("nl"),
    engine: str = Form(None),  # "openai" or "speech" (Azure Speech Service)
):
    """
    Upload and transcribe an audio file with speaker diarization.
    
    Args:
        file: The audio file to transcribe (max 25MB)
        language: Language code (default: nl for Dutch)
        engine: Transcription engine - "openai" (GPT-4o) or "speech" (Azure Speech Service)
    
    Returns:
        Job ID for tracking the transcription
    """
    # Use configured default if engine not specified
    selected_engine = engine or settings.transcription_engine
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension (native + convertible formats)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ACCEPTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(sorted(ACCEPTED_FORMATS))}"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file
    upload_path = Path(settings.upload_dir) / f"{job_id}{file_ext}"
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    # Initialize result
    result = TranscriptionResult(
        filename=file.filename,
        language=language,
        status="processing"
    )
    transcription_store[job_id] = result
    
    # Start transcription in background
    background_tasks.add_task(
        process_transcription,
        job_id=job_id,
        file_path=str(upload_path),
        language=language,
        engine=selected_engine,
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Transcription started (engine: {selected_engine})",
        "engine": selected_engine,
    }


async def process_transcription(job_id: str, file_path: str, language: str, engine: str = "speech"):
    """Background task to process transcription."""
    try:
        logger.info(
            "Background transcription started",
            extra={"job_id": job_id, "language": language, "file_path": file_path, "engine": engine},
        )
        
        if engine == "speech":
            # Use Azure Speech Service
            # NOTE: phrase_list temporarily disabled - causes Azure Speech to hang
            # from app.phrase_list import get_phrase_list
            transcriber = _get_speech_transcriber()
            result = await transcriber.transcribe_file(
                file_path,
                language,
                # phrase_list=get_phrase_list(),
            )
        else:
            # Use Azure OpenAI (gpt-4o-transcribe-diarize)
            transcriber = get_transcriber()
            result = await transcriber.transcribe_file(file_path, language)
        
        transcription_store[job_id] = result
        logger.info(
            "Background transcription finished",
            extra={"job_id": job_id, "status": result.status, "segments": len(result.segments), "engine": engine},
        )
    except Exception as e:
        if job_id in transcription_store:
            transcription_store[job_id].status = "error"
            transcription_store[job_id].error = str(e)
        logger.exception(
            "Background transcription failed",
            extra={"job_id": job_id, "file_path": file_path},
        )
    finally:
        # Clean up uploaded file
        try:
            os.remove(file_path)
            logger.info("Cleaned up uploaded file", extra={"job_id": job_id, "file_path": file_path})
        except:
            pass


@app.get("/api/transcription/{job_id}")
async def get_transcription(job_id: str):
    """
    Get the status and result of a transcription job.
    
    Args:
        job_id: The job ID from the transcribe endpoint
        
    Returns:
        Transcription status and results
    """
    if job_id not in transcription_store:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    result = transcription_store[job_id]
    return result.to_dict()


@app.get("/api/transcription/{job_id}/export/word")
async def export_word(job_id: str):
    """Export transcription as Word document."""
    if job_id not in transcription_store:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    result = transcription_store[job_id]
    if result.status != "completed":
        raise HTTPException(status_code=400, detail="Transcription not yet completed")
    
    buffer = ExportService.create_word_document(result)
    
    filename = f"transcriptie_{job_id[:8]}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/transcription/{job_id}/export/pdf")
async def export_pdf(job_id: str):
    """Export transcription as PDF document."""
    if job_id not in transcription_store:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    result = transcription_store[job_id]
    if result.status != "completed":
        raise HTTPException(status_code=400, detail="Transcription not yet completed")
    
    buffer = ExportService.create_pdf_document(result)
    
    filename = f"transcriptie_{job_id[:8]}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.delete("/api/transcription/{job_id}")
async def delete_transcription(job_id: str):
    """Delete a transcription result."""
    if job_id not in transcription_store:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    del transcription_store[job_id]
    return {"message": "Transcription deleted"}
