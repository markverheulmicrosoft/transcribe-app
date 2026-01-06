"""
Tests for the Transcription PoC API.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health and config endpoints."""
    
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
    
    def test_get_config(self, client):
        """Test the config endpoint."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "max_file_size_mb" in data
        assert "default_language" in data
        assert "supported_formats" in data
        assert "supported_languages" in data
        # Check default language
        assert data["default_language"] == "nl"
        # Check max file size for gpt-4o-transcribe-diarize
        assert data["max_file_size_mb"] == 25


class TestTranscriptionEndpoints:
    """Tests for transcription endpoints."""
    
    def test_transcribe_no_file(self, client):
        """Test transcribe endpoint without file."""
        response = client.post("/api/transcribe")
        assert response.status_code == 422  # Validation error
    
    def test_transcribe_invalid_format(self, client, tmp_path):
        """Test transcribe endpoint with invalid file format."""
        # Create a fake txt file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is not an audio file")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/transcribe",
                files={"file": ("test.txt", f, "text/plain")},
                data={"language": "nl"}
            )
        
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    
    def test_get_nonexistent_transcription(self, client):
        """Test getting a transcription that doesn't exist."""
        response = client.get("/api/transcription/nonexistent-id")
        assert response.status_code == 404
    
    def test_export_nonexistent_transcription_word(self, client):
        """Test exporting a transcription that doesn't exist."""
        response = client.get("/api/transcription/nonexistent-id/export/word")
        assert response.status_code == 404
    
    def test_export_nonexistent_transcription_pdf(self, client):
        """Test exporting a transcription that doesn't exist."""
        response = client.get("/api/transcription/nonexistent-id/export/pdf")
        assert response.status_code == 404


class TestStaticFiles:
    """Tests for static file serving."""
    
    def test_root_returns_html(self, client):
        """Test that root returns HTML page."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Transcriptie PoC" in response.text
