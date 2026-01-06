"""
Tests for audio conversion utilities.
"""
import pytest
from pathlib import Path

from app.services.audio_converter import (
    NATIVE_FORMATS,
    CONVERTIBLE_FORMATS,
    ACCEPTED_FORMATS,
    needs_conversion,
    is_ffmpeg_available,
)


class TestFormatSets:
    """Tests for format definitions."""
    
    def test_native_formats_exist(self):
        """Test that native formats are defined."""
        assert ".mp3" in NATIVE_FORMATS
        assert ".wav" in NATIVE_FORMATS
        assert ".m4a" in NATIVE_FORMATS
        assert ".webm" in NATIVE_FORMATS
    
    def test_convertible_formats_exist(self):
        """Test that convertible formats include ASF."""
        assert ".asf" in CONVERTIBLE_FORMATS
        assert ".wma" in CONVERTIBLE_FORMATS
        assert ".flac" in CONVERTIBLE_FORMATS
    
    def test_accepted_formats_is_union(self):
        """Test that accepted formats is union of native and convertible."""
        assert ACCEPTED_FORMATS == NATIVE_FORMATS | CONVERTIBLE_FORMATS
        assert ".mp3" in ACCEPTED_FORMATS  # native
        assert ".asf" in ACCEPTED_FORMATS  # convertible


class TestNeedsConversion:
    """Tests for needs_conversion function."""
    
    def test_native_format_no_conversion(self):
        """Native formats should not need conversion."""
        assert not needs_conversion("test.mp3")
        assert not needs_conversion("test.wav")
        assert not needs_conversion("test.m4a")
        assert not needs_conversion("/path/to/file.webm")
    
    def test_convertible_format_needs_conversion(self):
        """Convertible formats should need conversion."""
        assert needs_conversion("test.asf")
        assert needs_conversion("test.wma")
        assert needs_conversion("test.flac")
        assert needs_conversion("/path/to/recording.asf")
    
    def test_case_insensitive(self):
        """Extension check should be case insensitive."""
        assert needs_conversion("test.ASF")
        assert needs_conversion("test.Wma")
        assert not needs_conversion("test.MP3")


class TestFfmpegAvailability:
    """Tests for ffmpeg availability check."""
    
    def test_ffmpeg_check_returns_bool(self):
        """is_ffmpeg_available should return boolean."""
        result = is_ffmpeg_available()
        assert isinstance(result, bool)
