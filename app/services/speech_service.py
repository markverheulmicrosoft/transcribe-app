"""
Azure OpenAI transcription service using gpt-4o-transcribe-diarize model.
This model provides speech-to-text with built-in speaker diarization.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
from openai import AzureOpenAI

from app.config import get_settings
from app.services.audio_converter import (
    needs_conversion,
    convert_to_wav,
    is_ffmpeg_available,
)


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
            api_version="2025-01-01",  # Use latest API version for transcribe-diarize
            azure_endpoint=self.settings.azure_openai_endpoint
        )
    
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
            return result
        
        # Track if we created a converted file that needs cleanup
        converted_file_path: str | None = None
        file_to_transcribe = audio_file_path
        
        try:
            # Check if file needs conversion (ASF, WMA, etc.)
            if needs_conversion(audio_file_path):
                if on_progress:
                    on_progress("Converting audio format to WAV...")
                
                if not is_ffmpeg_available():
                    result.status = "error"
                    result.error = (
                        "This file format requires ffmpeg for conversion. "
                        "Please install ffmpeg or upload a supported format (MP3, WAV, M4A, MP4, WEBM)."
                    )
                    return result
                
                # Convert to WAV
                converted_file_path = audio_file_path.rsplit(".", 1)[0] + "_converted.wav"
                convert_to_wav(audio_file_path, converted_file_path)
                file_to_transcribe = converted_file_path
                
                if on_progress:
                    on_progress("Conversion complete, starting transcription...")
            
            # Check file size (25MB limit for gpt-4o-transcribe-diarize)
            file_size_mb = os.path.getsize(file_to_transcribe) / (1024 * 1024)
            if file_size_mb > 25:
                result.status = "error"
                result.error = f"File size ({file_size_mb:.1f}MB) exceeds 25MB limit for gpt-4o-transcribe-diarize"
                return result
            
            if on_progress:
                on_progress("Starting transcription with gpt-4o-transcribe-diarize...")
            
            # Open and send file to Azure OpenAI
            with open(file_to_transcribe, "rb") as audio_file:
                # Call the transcription API with diarization
                # The gpt-4o-transcribe-diarize model returns speaker labels
                response = self.client.audio.transcriptions.create(
                    model=self.settings.azure_openai_deployment_name,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",  # Get detailed response with timestamps
                    timestamp_granularities=["word", "segment"]
                )
            
            if on_progress:
                on_progress("Processing transcription response...")
            
            # Parse the response
            result.full_text = response.text
            result.duration_seconds = getattr(response, 'duration', 0.0)
            
            # Parse segments with speaker information
            # The diarize model includes speaker labels in the response
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    # Extract speaker ID from the segment
                    # gpt-4o-transcribe-diarize includes speaker info in segments
                    speaker_id = getattr(segment, 'speaker', None)
                    if speaker_id is None:
                        # Fallback: check for speaker in text or use default
                        speaker_id = self._extract_speaker_from_segment(segment)
                    
                    trans_segment = TranscriptionSegment(
                        speaker_id=speaker_id or "Speaker",
                        text=segment.text.strip(),
                        start_time=getattr(segment, 'start', 0.0),
                        end_time=getattr(segment, 'end', 0.0)
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
        
        finally:
            # Clean up converted file if we created one
            if converted_file_path and os.path.exists(converted_file_path):
                try:
                    os.remove(converted_file_path)
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
