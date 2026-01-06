"""
Audio conversion utilities using ffmpeg.
Converts unsupported formats (ASF, WMA, AVI, etc.) to WAV for transcription.
"""
import os
import subprocess
import shutil
from pathlib import Path


# Formats natively supported by gpt-4o-transcribe-diarize
NATIVE_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mpeg", ".mpga"}

# Formats we can convert using ffmpeg
CONVERTIBLE_FORMATS = {".asf", ".wma", ".avi", ".flv", ".ogg", ".flac", ".aac", ".wmv"}

# All accepted formats (native + convertible)
ACCEPTED_FORMATS = NATIVE_FORMATS | CONVERTIBLE_FORMATS


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is installed and available."""
    return shutil.which("ffmpeg") is not None


def needs_conversion(file_path: str) -> bool:
    """Check if the file needs to be converted before transcription."""
    ext = Path(file_path).suffix.lower()
    return ext in CONVERTIBLE_FORMATS


def convert_to_wav(input_path: str, output_path: str | None = None) -> str:
    """
    Convert audio file to WAV format using ffmpeg.
    
    Args:
        input_path: Path to the input audio file
        output_path: Optional output path. If not provided, creates a .wav 
                     file in the same directory.
    
    Returns:
        Path to the converted WAV file
        
    Raises:
        RuntimeError: If ffmpeg is not available or conversion fails
    """
    if not is_ffmpeg_available():
        raise RuntimeError(
            "ffmpeg is not installed. Please install ffmpeg to convert audio files.\n"
            "Ubuntu/Debian: sudo apt-get install ffmpeg\n"
            "macOS: brew install ffmpeg\n"
            "Windows: Download from https://ffmpeg.org/download.html"
        )
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Generate output path if not provided
    if output_path is None:
        input_path_obj = Path(input_path)
        output_path = str(input_path_obj.with_suffix(".wav"))
    
    # ffmpeg command to convert to WAV
    # -y: overwrite output file without asking
    # -i: input file
    # -acodec pcm_s16le: 16-bit PCM audio codec (standard WAV)
    # -ar 16000: 16kHz sample rate (good for speech)
    # -ac 1: mono (reduces file size, good for speech)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for large files
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")
        
        if not os.path.exists(output_path):
            raise RuntimeError("Conversion completed but output file not found")
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audio conversion timed out (>5 minutes)")
    except Exception as e:
        raise RuntimeError(f"Audio conversion failed: {str(e)}")


def get_audio_duration(file_path: str) -> float | None:
    """
    Get the duration of an audio file in seconds using ffprobe.
    
    Returns None if duration cannot be determined.
    """
    if not is_ffmpeg_available():
        return None
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        pass
    
    return None


def get_audio_info(file_path: str) -> dict:
    """
    Get audio file information using ffprobe.
    
    Returns dict with format, duration, sample_rate, channels, etc.
    """
    info = {
        "format": Path(file_path).suffix.lower(),
        "duration": None,
        "sample_rate": None,
        "channels": None,
        "codec": None,
    }
    
    if not is_ffmpeg_available():
        return info
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
        "-of", "json",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            if "format" in data and "duration" in data["format"]:
                info["duration"] = float(data["format"]["duration"])
            
            if "streams" in data and len(data["streams"]) > 0:
                stream = data["streams"][0]
                info["codec"] = stream.get("codec_name")
                info["sample_rate"] = int(stream["sample_rate"]) if "sample_rate" in stream else None
                info["channels"] = int(stream["channels"]) if "channels" in stream else None
                
    except (subprocess.TimeoutExpired, ValueError, KeyError):
        pass
    
    return info
