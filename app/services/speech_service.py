"""
Azure OpenAI transcription service using gpt-4o-transcribe-diarize model.
This model provides speech-to-text with built-in speaker diarization.
"""
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
from openai import AzureOpenAI
from openai import BadRequestError

from app.config import get_settings
from app.services.audio_converter import (
    needs_conversion,
    convert_to_wav,
    is_ffmpeg_available,
)


logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a segment of transcribed speech."""
    speaker_id: str
    text: str
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class TranscriptionResult:
    """Complete transcription result with all segments."""
    segments: list[TranscriptionSegment] = field(default_factory=list)
    full_text: str = ""
    status: str = "pending"
    error: str | None = None
    filename: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    language: str = "nl"
    duration_seconds: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "segments": [
                {
                    "speaker_id": s.speaker_id,
                    "text": s.text,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                }
                for s in self.segments
            ],
            "full_text": self.full_text,
            "status": self.status,
            "error": self.error,
            "filename": self.filename,
            "created_at": self.created_at.isoformat(),
            "language": self.language,
            "duration_seconds": self.duration_seconds,
        }
    
    def get_formatted_transcript(self) -> str:
        """Get formatted transcript with speaker labels."""
        lines = []
        current_speaker = None
        current_text = []
        
        for segment in self.segments:
            if segment.speaker_id != current_speaker:
                if current_text:
                    lines.append(f"{current_speaker}: {' '.join(current_text)}")
                current_speaker = segment.speaker_id
                current_text = [segment.text]
            else:
                current_text.append(segment.text)
        
        if current_text:
            lines.append(f"{current_speaker}: {' '.join(current_text)}")
        
        return "\n\n".join(lines)


class SpeechTranscriber:
    """
    Azure OpenAI transcriber using gpt-4o-transcribe-diarize model.
    Provides speech-to-text with automatic speaker diarization.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._validate_settings()
        self.client = self._create_client()
    
    def _validate_settings(self):
        """Validate that required settings are present."""
        if not self.settings.azure_openai_endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is not set. "
                "Please configure it in your .env file."
            )
        if not self.settings.azure_openai_api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY is not set. "
                "Please configure it in your .env file."
            )
    
    def _create_client(self) -> AzureOpenAI:
        """Create Azure OpenAI client."""
        return AzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            azure_endpoint=self.settings.azure_openai_endpoint
        )

    def _get_segment_speaker_label(self, segment) -> str | None:
        """Best-effort extraction of a diarization speaker label from a segment."""
        for attr in ["speaker", "speaker_id", "speakerId", "speaker_label", "speakerLabel"]:
            if hasattr(segment, attr):
                value = getattr(segment, attr)
                if value is not None:
                    return str(value)
        return None

    def _summarize_response_for_logs(self, response) -> dict:
        """Return a small, safe summary for logging (no transcript text)."""
        summary: dict = {
            "has_text": hasattr(response, "text"),
            "text_len": None,
            "has_segments": hasattr(response, "segments"),
            "segments_count": None,
            "duration": getattr(response, "duration", None),
        }
        try:
            text = getattr(response, "text", None)
            if isinstance(text, str):
                summary["text_len"] = len(text)
        except Exception:
            pass

        try:
            segments = getattr(response, "segments", None)
            if segments is not None:
                summary["segments_count"] = len(segments)
        except Exception:
            pass

        # Inspect a single segment for speaker-like fields (names only)
        try:
            segments = getattr(response, "segments", None) or []
            if segments:
                seg0 = segments[0]
                speaker_fields = [
                    name
                    for name in ("speaker", "speaker_id", "speakerId", "speaker_label", "speakerLabel")
                    if hasattr(seg0, name)
                ]
                summary["segment0_speaker_fields"] = speaker_fields
        except Exception:
            pass

        return summary
    
    async def transcribe_file(
        self,
        audio_file_path: str,
        language: str = "nl",
        on_progress: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file with speaker diarization using gpt-4o-transcribe-diarize.
        
        Args:
            audio_file_path: Path to the audio file (max 25MB)
            language: Language code (e.g., 'nl' for Dutch, 'en' for English)
            on_progress: Optional callback for progress updates
            
        Returns:
            TranscriptionResult with segments and speaker information
        """
        result = TranscriptionResult(
            filename=os.path.basename(audio_file_path),
            language=language
        )
        
        if not os.path.exists(audio_file_path):
            result.status = "error"
            result.error = f"Audio file not found: {audio_file_path}"
            logger.warning(
                "Audio file missing",
                    extra={"path": audio_file_path, "audio_filename": result.filename},
            )
            return result
        
        # Track if we created a converted file that needs cleanup
        converted_file_path: str | None = None
        file_to_transcribe = audio_file_path
        
        try:
            logger.info(
                "Starting transcription",
                extra={
                    "audio_filename": result.filename,
                    "language": language,
                    "deployment": self.settings.azure_openai_deployment_name,
                    "api_version": self.settings.azure_openai_api_version,
                },
            )

            # Check if file needs conversion (ASF, WMA, etc.)
            conversion_needed = needs_conversion(audio_file_path)
            logger.info(
                "Checked conversion requirement",
                extra={"audio_filename": result.filename, "needs_conversion": conversion_needed},
            )

            if conversion_needed:
                if on_progress:
                    on_progress("Converting audio format to WAV...")
                
                ffmpeg_ok = is_ffmpeg_available()
                logger.info(
                    "Checked ffmpeg availability",
                    extra={"audio_filename": result.filename, "ffmpeg_available": ffmpeg_ok},
                )

                if not ffmpeg_ok:
                    result.status = "error"
                    result.error = (
                        "This file format requires ffmpeg for conversion. "
                        "Please install ffmpeg or upload a supported format (MP3, WAV, M4A, MP4, WEBM)."
                    )
                    return result
                
                # Convert to WAV
                converted_file_path = audio_file_path.rsplit(".", 1)[0] + "_converted.wav"
                logger.info(
                    "Starting conversion to WAV",
                    extra={"audio_filename": result.filename, "output_path": converted_file_path},
                )
                convert_to_wav(audio_file_path, converted_file_path)
                file_to_transcribe = converted_file_path

                logger.info(
                    "Conversion complete",
                    extra={"audio_filename": result.filename, "file_to_transcribe": file_to_transcribe},
                )
                
                if on_progress:
                    on_progress("Conversion complete, starting transcription...")
            
            # Check file size (25MB limit for gpt-4o-transcribe-diarize)
            file_size_mb = os.path.getsize(file_to_transcribe) / (1024 * 1024)
            logger.info(
                "Checked file size",
                extra={"audio_filename": result.filename, "file_size_mb": round(file_size_mb, 3)},
            )
            if file_size_mb > 25:
                result.status = "error"
                result.error = f"File size ({file_size_mb:.1f}MB) exceeds 25MB limit for gpt-4o-transcribe-diarize"
                return result
            
            if on_progress:
                on_progress("Starting transcription with gpt-4o-transcribe-diarize...")

            logger.info(
                "Prepared audio file",
                extra={
                    "audio_filename": result.filename,
                    "file_size_mb": round(file_size_mb, 3),
                    "converted": converted_file_path is not None,
                },
            )
            
            # Open and send file to Azure OpenAI
            with open(file_to_transcribe, "rb") as audio_file:
                requested_format = (self.settings.azure_openai_transcription_response_format or "json").strip()

                # Diarization deployments require chunking_strategy. If not explicitly configured,
                # default to 'auto' when the deployment name suggests a diarization model.
                configured_chunking = (self.settings.azure_openai_chunking_strategy_type or "").strip() or None
                inferred_chunking = None
                if not configured_chunking and "diarize" in (self.settings.azure_openai_deployment_name or "").lower():
                    inferred_chunking = "auto"

                effective_chunking = configured_chunking or inferred_chunking

                # Build API call parameters.
                # chunking_strategy must be passed as a direct kwarg (string "auto"), NOT via extra_body.
                create_kwargs: dict = {
                    "model": self.settings.azure_openai_deployment_name,
                    "file": audio_file,
                    "language": language,
                    "response_format": requested_format,
                    "temperature": 0,  # Deterministic output for better quality
                }
                if effective_chunking:
                    create_kwargs["chunking_strategy"] = effective_chunking

                logger.info(
                    "Calling Azure transcription",
                    extra={
                        "deployment": self.settings.azure_openai_deployment_name,
                        "language": language,
                        "response_format": create_kwargs.get("response_format"),
                        "chunking_strategy": effective_chunking,
                        "temperature": 0,
                        "chunking_inferred": inferred_chunking is not None and configured_chunking is None,
                    },
                )

                try:
                    response = self.client.audio.transcriptions.create(**create_kwargs)
                except BadRequestError as e:
                    # If the configured response_format is unsupported by the deployed model, retry with json.
                    message = str(e)
                    if (
                        create_kwargs.get("response_format") != "json"
                        and "response_format" in message
                        and "not compatible" in message
                    ):
                        logger.warning(
                            "response_format rejected by model; retrying with json",
                            extra={"requested": create_kwargs.get("response_format")},
                        )
                        if on_progress:
                            on_progress("Azure rejected response_format; retrying with json...")
                        create_kwargs["response_format"] = "json"
                        response = self.client.audio.transcriptions.create(**create_kwargs)
                    else:
                        raise
            
            if on_progress:
                on_progress("Processing transcription response...")

            logger.info(
                "Received transcription response",
                extra=self._summarize_response_for_logs(response),
            )
            
            # Parse the response
            result.full_text = getattr(response, "text", "") or ""
            result.duration_seconds = float(getattr(response, "duration", 0.0) or 0.0)

            logger.info(
                "Parsed transcription top-level fields",
                extra={
                    "audio_filename": result.filename,
                    "full_text_len": len(result.full_text),
                    "duration_seconds": result.duration_seconds,
                },
            )
            
            # Parse segments with speaker information
            # The diarize model includes speaker labels in the response
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    # Extract speaker ID from the segment
                    # gpt-4o-transcribe-diarize includes speaker info in segments
                    speaker_id = self._get_segment_speaker_label(segment)
                    if speaker_id is None:
                        # Fallback: check for speaker in text or use default
                        speaker_id = self._extract_speaker_from_segment(segment)
                    
                    trans_segment = TranscriptionSegment(
                        speaker_id=speaker_id or "Speaker",
                        text=(getattr(segment, "text", "") or "").strip(),
                        start_time=float(getattr(segment, "start", 0.0) or 0.0),
                        end_time=float(getattr(segment, "end", 0.0) or 0.0)
                    )
                    result.segments.append(trans_segment)
            else:
                # If no segments, create a single segment with full text
                result.segments.append(TranscriptionSegment(
                    speaker_id="Speaker 1",
                    text=result.full_text,
                    start_time=0.0,
                    end_time=result.duration_seconds
                ))
            
            result.status = "completed"
            
            if on_progress:
                on_progress(f"Transcription complete: {len(result.segments)} segments")
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            if on_progress:
                on_progress(f"Error: {str(e)}")

            logger.exception(
                "Transcription failed",
                extra={"audio_filename": result.filename, "language": language},
            )
        
        finally:
            # Clean up converted file if we created one
            if converted_file_path and os.path.exists(converted_file_path):
                try:
                    os.remove(converted_file_path)
                    logger.info(
                        "Cleaned up converted file",
                        extra={"audio_filename": result.filename, "converted_file_path": converted_file_path},
                    )
                except OSError:
                    pass  # Ignore cleanup errors
        
        return result
    
    def _extract_speaker_from_segment(self, segment) -> str:
        """
        Extract speaker ID from segment data.
        The gpt-4o-transcribe-diarize model includes speaker info.
        """
        # Check common attribute names for speaker
        for attr in ['speaker', 'speaker_id', 'speakerId', 'speaker_label']:
            if hasattr(segment, attr):
                value = getattr(segment, attr)
                if value is not None:
                    return f"Speaker {value}" if isinstance(value, int) else str(value)
        
        # Check if segment has an id that indicates speaker
        if hasattr(segment, 'id'):
            segment_id = segment.id
            if isinstance(segment_id, str) and 'speaker' in segment_id.lower():
                return segment_id
        
        return "Speaker"


# Singleton instance
_transcriber: SpeechTranscriber | None = None


def get_transcriber() -> SpeechTranscriber:
    """Get singleton transcriber instance."""
    global _transcriber
    if _transcriber is None:
        _transcriber = SpeechTranscriber()
    return _transcriber
