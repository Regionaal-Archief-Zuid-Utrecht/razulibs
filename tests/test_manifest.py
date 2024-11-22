import pytest
import os
import json
from datetime import datetime
from razu.manifest import Manifest
from razu.razuconfig import RazuConfig
from razu.config import Config

@pytest.fixture(autouse=True)
def reset_config():
    """Reset the Config singleton between tests."""
    Config.reset()
    RazuConfig.reset()
    yield
    Config.reset()
    RazuConfig.reset()

@pytest.fixture
def config():
    """Setup de benodigde configuratie voor alle tests."""
    Config.reset()  # Ensure clean state before creating new config
    return RazuConfig(
        archive_creator_id="G312",
        archive_id="661"
    )

def test_manifest_initialization(tmp_path, config):
    """Test of een manifest correct wordt geïnitialiseerd."""
    # Test initialisatie zonder bestaand manifest bestand
    manifest = Manifest(str(tmp_path), config=config)
    assert manifest.is_valid == False
    assert manifest.files == {}

    # Test initialisatie met bestaand manifest bestand
    manifest_file = os.path.join(tmp_path, config.manifest_filename)
    with open(manifest_file, "w") as f:
        json.dump({}, f)

    manifest = Manifest(str(tmp_path), config=config)
    assert manifest.is_valid == True
    assert manifest.files == {}

def test_manifest_add_entry(tmp_path, config):
    """Test het toevoegen van een bestand aan het manifest."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Voeg een test bestand toe
    test_date = datetime.now().isoformat()
    manifest.add_entry("test.txt", "md5hash123", test_date)
    
    assert "test.txt" in manifest.files
    assert manifest.files["test.txt"]["MD5Hash"] == "md5hash123"
    assert manifest.files["test.txt"]["MD5HashDate"] == test_date

def test_manifest_save_and_load(tmp_path, config):
    """Test het opslaan en laden van een manifest bestand."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Voeg een test bestand toe en sla op
    test_date = datetime.now().isoformat()
    manifest.add_entry("test.txt", "md5hash123", test_date)
    manifest.save()
    
    # Laad een nieuw manifest object
    manifest2 = Manifest(str(tmp_path), config=config)
    assert "test.txt" in manifest2.files
    assert manifest2.files["test.txt"]["MD5Hash"] == "md5hash123"
    assert manifest2.files["test.txt"]["MD5HashDate"] == test_date

def test_manifest_verify_missing_file(tmp_path, config):
    """Test verificatie wanneer een bestand ontbreekt."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Voeg een test bestand toe dat niet bestaat
    manifest.add_entry("missing.txt", "md5hash123", datetime.now().isoformat())
    
    with pytest.raises(ValueError) as excinfo:
        manifest.verify()
    assert "Missing files" in str(excinfo.value)
    assert "missing.txt" in str(excinfo.value)

def test_manifest_verify_extra_file(tmp_path, config):
    """Test verificatie wanneer er een extra bestand aanwezig is."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Maak een bestand dat niet in het manifest staat
    with open(os.path.join(tmp_path, "extra.txt"), "w") as f:
        f.write("test")
    
    with pytest.raises(ValueError) as excinfo:
        manifest.verify()
    assert "Extra files" in str(excinfo.value)
    assert "extra.txt" in str(excinfo.value)

def test_manifest_verify_ignore_options(tmp_path, config):
    """Test dat verify() de juiste opties respecteert."""
    manifest = Manifest(str(tmp_path), config=config)
    manifest.create_from_directory()
    
    # Maak een bestand dat niet in het manifest staat
    with open(os.path.join(tmp_path, "ignore.txt"), "w") as f:
        f.write("test")
    
    # Should not raise an error when ignore_extra is True
    manifest.verify(ignore_extra=True)
    assert manifest.is_valid == True

def test_manifest_append(tmp_path, config):
    """Test het toevoegen van ontbrekende bestanden aan het manifest."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Create empty manifest first
    manifest.create_from_directory()
    
    # Maak een bestand dat niet in het manifest staat
    test_file = os.path.join(tmp_path, "append.txt")
    with open(test_file, "w") as f:
        f.write("test")
    
    manifest.append()
    assert "append.txt" in manifest.files

def test_manifest_update_entry(tmp_path, config):
    """Test het bijwerken van een bestaand manifest entry."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Voeg een test bestand toe
    manifest.add_entry("test.txt", "md5hash123", datetime.now().isoformat())
    
    # Voeg extra informatie toe
    manifest.extend_entry("test.txt", {"extra": "info"})
    
    assert manifest.files["test.txt"]["extra"] == "info"

def test_manifest_get_filenames(tmp_path, config):
    """Test het ophalen van bestandsnamen uit het manifest."""
    manifest = Manifest(str(tmp_path), config=config)
    
    # Voeg test bestanden toe
    manifest.add_entry("test1.txt", "md5hash123", datetime.now().isoformat())
    manifest.add_entry("test2.txt", "md5hash456", datetime.now().isoformat())
    
    filenames = manifest.get_filenames()
    assert "test1.txt" in filenames
    assert "test2.txt" in filenames
