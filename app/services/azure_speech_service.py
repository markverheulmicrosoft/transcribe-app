"""
Azure Speech Fast Transcription API with speaker diarization.
Uses the REST API for synchronous transcription of audio files.
Better Dutch language support than OpenAI models.

Docs: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/fast-transcription-create
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import httpx

from app.config import get_settings
from app.services.audio_converter import (
    convert_to_wav,
    extract_audio_from_container,
    is_ffmpeg_available,
)

logger = logging.getLogger(__name__)

# API version for Fast Transcription (2025-10-15 has improved diarization)
FAST_TRANSCRIPTION_API_VERSION = "2025-10-15"

# Formats natively supported by Azure Speech Fast Transcription
# Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription-audio-data
AZURE_SPEECH_NATIVE_FORMATS = {
    ".wav", ".mp3", ".ogg", ".opus", ".flac", ".wma", ".aac", ".webm", ".amr", ".speex"
}

# Container formats that can have audio extracted without re-encoding
# (e.g., ASF usually contains WMA audio which Azure Speech supports)
ASF_LIKE_CONTAINERS = {".asf"}

# Formats that need full conversion (re-encoding) for Azure Speech
AZURE_SPEECH_CONVERTIBLE_FORMATS = {".avi", ".flv", ".wmv", ".m4a", ".mp4"}


def _needs_conversion_for_speech(file_path: str) -> bool:
    """Check if the file needs conversion for Azure Speech Fast Transcription."""
    ext = os.path.splitext(file_path)[1].lower()
    # Only convert if it's not in the native formats and not an extractable container
    return ext not in AZURE_SPEECH_NATIVE_FORMATS and ext not in ASF_LIKE_CONTAINERS


def _needs_extraction_for_speech(file_path: str) -> bool:
    """Check if the file is a container that can have audio extracted."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ASF_LIKE_CONTAINERS


@dataclass
class SpeechSegment:
    """Represents a segment of transcribed speech."""
    speaker_id: str
    text: str
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class SpeechTranscriptionResult:
    """Complete transcription result with all segments."""
    segments: list[SpeechSegment] = field(default_factory=list)
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


class AzureSpeechTranscriber:
    """
    Azure Speech Fast Transcription API with speaker diarization.
    
    Features:
    - Direct file upload (no Blob Storage needed)
    - Up to 2 hours / 300MB per file
    - Excellent Dutch (nl-NL) language support
    - Speaker diarization built-in
    - Synchronous response (fast — roughly 1/4 of audio duration)
    """

    def __init__(self):
        self.settings = get_settings()
        self._validate_settings()

    def _validate_settings(self):
        """Validate that required settings are present."""
        if not self.settings.azure_speech_key:
            raise ValueError(
                "AZURE_SPEECH_KEY is not set. "
                "Please configure it in your .env file."
            )
        if not self.settings.azure_speech_region:
            raise ValueError(
                "AZURE_SPEECH_REGION is not set. "
                "Please configure it in your .env file."
            )

    def _get_locale(self, language: str) -> str:
        """Convert short language code to Azure Speech locale."""
        language_map = {
            "nl": "nl-NL",
            "en": "en-US",
            "de": "de-DE",
            "fr": "fr-FR",
            "es": "es-ES",
            "it": "it-IT",
        }
        return language_map.get(language, f"{language}-{language.upper()}")

    def _get_content_type(self, file_path: str) -> str:
        """Get content type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".m4a": "audio/mp4",
            ".mp4": "audio/mp4",
            ".webm": "audio/webm",
            ".wma": "audio/x-ms-wma",
            ".aac": "audio/aac",
        }
        return content_types.get(ext, "audio/wav")

    async def transcribe_file(
        self,
        audio_file_path: str,
        language: str = "nl",
        on_progress: Callable[[str], None] | None = None,
        phrase_list: list[str] | None = None,
    ) -> SpeechTranscriptionResult:
        """
        Transcribe an audio file with speaker diarization using Azure Speech Fast Transcription API.

        Args:
            audio_file_path: Path to the audio file (max 2 hours / 300MB)
            language: Language code (e.g., 'nl' for Dutch, 'en' for English)
            on_progress: Optional callback for progress updates
            phrase_list: Optional list of words/phrases to boost recognition
                         (e.g., ["Raad van State", "appellant", "verweerder"])

        Returns:
            SpeechTranscriptionResult with segments and speaker information
        """
        result = SpeechTranscriptionResult(
            filename=os.path.basename(audio_file_path),
            language=language,
        )

        if not os.path.exists(audio_file_path):
            result.status = "error"
            result.error = f"Audio file not found: {audio_file_path}"
            logger.warning(
                "Audio file missing",
                extra={"path": audio_file_path, "audio_filename": result.filename},
            )
            return result

        # Track if we created a converted/extracted file that needs cleanup
        converted_file_path: str | None = None
        file_to_transcribe = audio_file_path

        try:
            logger.info(
                "Starting Azure Speech Fast Transcription",
                extra={
                    "audio_filename": result.filename,
                    "language": language,
                    "region": self.settings.azure_speech_region,
                },
            )

            # Check file size (300MB limit for Fast Transcription)
            file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
            if file_size_mb > 300:
                result.status = "error"
                result.error = f"File size ({file_size_mb:.1f}MB) exceeds 300MB limit for Fast Transcription"
                return result

            # Check if we need to extract audio from container (ASF -> WMA, no quality loss)
            if _needs_extraction_for_speech(audio_file_path):
                if on_progress:
                    on_progress("Extracting audio from container (no re-encoding)...")

                if not is_ffmpeg_available():
                    result.status = "error"
                    result.error = (
                        "This file format requires ffmpeg for extraction. "
                        "Please install ffmpeg or upload a supported format."
                    )
                    return result

                converted_file_path = audio_file_path.rsplit(".", 1)[0] + "_extracted.wma"
                logger.info(
                    "Extracting audio from ASF container (no re-encoding, preserves quality)",
                    extra={"audio_filename": result.filename, "output_path": converted_file_path},
                )
                extract_audio_from_container(audio_file_path, converted_file_path)
                file_to_transcribe = converted_file_path

                logger.info("Extraction complete", extra={"audio_filename": result.filename})

            # Check if we need full conversion (re-encoding)
            elif _needs_conversion_for_speech(audio_file_path):
                if on_progress:
                    on_progress("Converting audio format...")

                if not is_ffmpeg_available():
                    result.status = "error"
                    result.error = (
                        "This file format requires ffmpeg for conversion. "
                        "Please install ffmpeg or upload a supported format."
                    )
                    return result

                converted_file_path = audio_file_path.rsplit(".", 1)[0] + "_speech_converted.wav"
                logger.info(
                    "Converting audio for Azure Speech (re-encoding)",
                    extra={"audio_filename": result.filename, "output_path": converted_file_path},
                )
                convert_to_wav(audio_file_path, converted_file_path)
                file_to_transcribe = converted_file_path

                logger.info("Conversion complete", extra={"audio_filename": result.filename})

            if on_progress:
                on_progress("Uploading to Azure Speech Fast Transcription...")

            # Build the API endpoint
            endpoint = (
                f"https://{self.settings.azure_speech_region}.api.cognitive.microsoft.com"
                f"/speechtotext/transcriptions:transcribe?api-version={FAST_TRANSCRIPTION_API_VERSION}"
            )

            # Build the definition with diarization enabled
            # Note: The docs example shows {"maxSpeakers": 2, "enabled": true}
            locale = self._get_locale(language)
            definition = {
                "locales": [locale],
                "diarization": {
                    "maxSpeakers": 10,  # Support up to 10 speakers in meetings
                    "enabled": True,
                },
                "profanityFilterMode": "None",  # Keep original text
            }

            # Add phrase list if provided (improves recognition of domain-specific terms)
            if phrase_list:
                definition["phraseList"] = {"phrases": phrase_list}
                logger.info(
                    "Using phrase list for improved recognition",
                    extra={
                        "audio_filename": result.filename,
                        "phrase_count": len(phrase_list),
                        "phrases_sample": phrase_list[:5],
                    },
                )

            logger.info(
                "Calling Azure Speech Fast Transcription API",
                extra={
                    "audio_filename": result.filename,
                    "locale": locale,
                    "endpoint": endpoint,
                    "definition": json.dumps(definition),
                    "file_size_mb": round(file_size_mb, 2),
                },
            )

            if on_progress:
                on_progress("Transcribing audio (this may take a few minutes)...")

            # Make the API request
            content_type = self._get_content_type(file_to_transcribe)
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
                with open(file_to_transcribe, "rb") as audio_file:
                    files = {
                        "audio": (os.path.basename(file_to_transcribe), audio_file, content_type),
                    }
                    data = {
                        "definition": json.dumps(definition),
                    }
                    headers = {
                        "Ocp-Apim-Subscription-Key": self.settings.azure_speech_key,
                    }

                    response = await client.post(
                        endpoint,
                        files=files,
                        data=data,
                        headers=headers,
                    )

            logger.info(
                "Received Azure Speech response",
                extra={
                    "audio_filename": result.filename,
                    "status_code": response.status_code,
                },
            )

            if response.status_code != 200:
                error_text = response.text
                result.status = "error"
                result.error = f"Azure Speech API error ({response.status_code}): {error_text}"
                logger.error(
                    "Azure Speech API error",
                    extra={
                        "audio_filename": result.filename,
                        "status_code": response.status_code,
                        "error": error_text,
                    },
                )
                return result

            if on_progress:
                on_progress("Processing transcription results...")

            # Parse the response
            response_data = response.json()

            # Log the full response for debugging
            logger.info(
                "Azure Speech API response structure",
                extra={
                    "audio_filename": result.filename,
                    "has_combinedPhrases": "combinedPhrases" in response_data,
                    "has_phrases": "phrases" in response_data,
                    "phrases_count": len(response_data.get("phrases", [])),
                    "first_phrase_has_speaker": (
                        response_data.get("phrases", [{}])[0].get("speaker") is not None
                        if response_data.get("phrases") else False
                    ),
                    "response_keys": list(response_data.keys()),
                },
            )

            # Log first few phrases to see speaker data
            for i, phrase in enumerate(response_data.get("phrases", [])[:3]):
                logger.info(
                    f"Phrase {i} sample",
                    extra={
                        "audio_filename": result.filename,
                        "phrase_keys": list(phrase.keys()),
                        "speaker": phrase.get("speaker"),
                        "text": phrase.get("text", "")[:50],
                    },
                )

            # Extract duration
            duration_ms = response_data.get("durationMilliseconds", 0)
            result.duration_seconds = duration_ms / 1000.0

            # Extract combined text
            combined_phrases = response_data.get("combinedPhrases", [])
            if combined_phrases:
                result.full_text = " ".join(cp.get("text", "") for cp in combined_phrases)

            # Extract phrases with speaker info
            phrases = response_data.get("phrases", [])
            
            for phrase in phrases:
                text = phrase.get("text", "").strip()
                if not text:
                    continue

                # Get timing
                offset_ms = phrase.get("offsetMilliseconds", 0)
                duration_phrase_ms = phrase.get("durationMilliseconds", 0)
                start_time = offset_ms / 1000.0
                end_time = (offset_ms + duration_phrase_ms) / 1000.0

                # Get speaker (if diarization is enabled)
                speaker = phrase.get("speaker")
                if speaker is not None:
                    speaker_id = f"Speaker {speaker + 1}"  # 0-indexed to 1-indexed
                else:
                    speaker_id = "Speaker"

                segment = SpeechSegment(
                    speaker_id=speaker_id,
                    text=text,
                    start_time=start_time,
                    end_time=end_time,
                )
                result.segments.append(segment)

            # If no segments but we have full text, create a single segment
            if not result.segments and result.full_text:
                result.segments.append(SpeechSegment(
                    speaker_id="Speaker 1",
                    text=result.full_text,
                    start_time=0.0,
                    end_time=result.duration_seconds,
                ))

            result.status = "completed"

            logger.info(
                "Azure Speech transcription complete",
                extra={
                    "audio_filename": result.filename,
                    "segments_count": len(result.segments),
                    "duration_seconds": result.duration_seconds,
                    "full_text_len": len(result.full_text),
                },
            )

            if on_progress:
                on_progress(f"Transcription complete: {len(result.segments)} segments")

        except httpx.TimeoutException:
            result.status = "error"
            result.error = "Request timed out. The audio file may be too long. Try a shorter file."
            logger.exception(
                "Azure Speech request timed out",
                extra={"audio_filename": result.filename},
            )

        except Exception as e:
            result.status = "error"
            result.error = str(e)
            if on_progress:
                on_progress(f"Error: {str(e)}")

            logger.exception(
                "Azure Speech transcription failed",
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
                    pass

        return result


# Singleton instance
_speech_transcriber: AzureSpeechTranscriber | None = None


def get_speech_transcriber() -> AzureSpeechTranscriber:
    """Get singleton Azure Speech transcriber instance."""
    global _speech_transcriber
    if _speech_transcriber is None:
        _speech_transcriber = AzureSpeechTranscriber()
    return _speech_transcriber
