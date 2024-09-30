import pytest
import os
import json
from unittest.mock import patch, mock_open, MagicMock
from razu.manifest import Manifest



@pytest.fixture
def mock_manifest():
    """Fixture om een mock manifest aan te maken."""
    with patch("razu.manifest.Manifest.calculate_md5", return_value="dummy_checksum"):
        manifest = Manifest("/mock_directory", "mock_manifest.json")
        yield manifest


@patch("os.path.exists", return_value=False)  # Simuleer dat het manifest nog niet bestaat
@patch("os.walk")
def test_create_from_directory(mock_os_walk, mock_path_exists, mock_manifest):
    """Test dat een manifest correct wordt aangemaakt vanuit een directory."""
    mock_os_walk.return_value = [("/mock_directory", [], ["file1.txt", "file2.txt"])]
    
    with patch("builtins.open", mock_open()) as mock_file:
        mock_manifest.create_from_directory()
        
        # Controleer of de bestanden correct in het manifest zijn opgenomen
        assert "file1.txt" in mock_manifest.files
        assert "file2.txt" in mock_manifest.files
        mock_file.assert_called_once_with("/mock_directory/mock_manifest.json", "w")


@patch("os.path.exists", return_value=True)  # Simuleer dat het manifest al bestaat
@patch("builtins.open", mock_open(read_data=json.dumps({"file1.txt": {"MD5Hash": "dummy_checksum"}})))
def test_verify_success(mock_path_exists, mock_manifest):
    """Test dat de manifest validatie correct is."""
    mock_manifest.files = {
        "file1.txt": {"MD5Hash": "dummy_checksum"},
        "file2.txt": {"MD5Hash": "dummy_checksum"}
    }

    with patch("os.walk", return_value=[("/mock_directory", [], ["file1.txt", "file2.txt"])]):
        errors = mock_manifest.verify()
        
        assert errors["missing_files"] == []
        assert errors["checksum_mismatch"] == []
        assert errors["extra_files"] == []


@patch("os.path.exists", return_value=True)
@patch("os.walk")
def test_append_new_files(mock_os_walk, mock_path_exists, mock_manifest):
    """Test dat nieuwe bestanden worden toegevoegd aan het manifest."""
    # Stel dat het manifest al bestaat met één bestand
    manifest_data = json.dumps({"file1.txt": {"MD5Hash": "dummy_checksum"}})

    # Mock voor het openen van het manifestbestand (zowel voor lezen als schrijven)
    with patch("builtins.open", mock_open(read_data=manifest_data)) as mock_file:
        mock_os_walk.return_value = [("/mock_directory", [], ["file1.txt", "file2.txt"])]

        # Voer de append operatie uit
        mock_manifest.append()

        # Controleer of het nieuwe bestand ('file2.txt') is toegevoegd
        assert "file2.txt" in mock_manifest.files

        # Controleer dat open() is aangeroepen voor lezen en schrijven
        mock_file.assert_any_call("/mock_directory/mock_manifest.json", "r")  # Voor het laden van het manifest
        mock_file.assert_any_call("/mock_directory/mock_manifest.json", "w")  # Voor het opslaan van het manifest
