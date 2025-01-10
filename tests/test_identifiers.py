import pytest
from pathlib import Path
from razu.config import Config
from razu.identifiers import Identifiers

@pytest.fixture
def test_config_path():
    """Return the path to the test configuration file."""
    return str(Path(__file__).parent / 'fixtures' / 'test_identifiers.yaml')

@pytest.fixture
def config(test_config_path):
    """Create a Config instance with test configuration."""
    Config.reset()  # Reset any existing configuration
    return Config.initialize(config_file=test_config_path)

@pytest.fixture
def identifiers(config):
    """Create an Identifiers instance with test configuration."""
    return Identifiers(config)

def test_uid_base(identifiers):
    """Test generatie van de UID base."""
    expected = "NL-WbDRAZU-G0321-661"
    assert identifiers.uid_base == expected

def test_cdn_base_uri(identifiers):
    """Test generatie van de CDN base URI."""
    expected = "https://g0321.opslag.razu.nl/"
    assert identifiers.cdn_base_uri == expected

def test_object_uri_prefix(identifiers):
    """Test generatie van de object URI prefix."""
    expected = "https://data.razu.nl/id/object/NL-WbDRAZU-G0321-661"
    assert identifiers.object_uri_prefix == expected

def test_event_uri_prefix(identifiers):
    """Test generatie van de event URI prefix."""
    expected = "https://data.razu.nl/id/event/NL-WbDRAZU-G0321-661"
    assert identifiers.event_uri_prefix == expected

def test_manifest_filename(identifiers):
    """Test generatie van de manifest bestandsnaam."""
    expected = "NL-WbDRAZU-G0321-661.manifest.json"
    assert identifiers.manifest_filename == expected

def test_eventlog_filename(identifiers):
    """Test generatie van de eventlog bestandsnaam."""
    expected = "NL-WbDRAZU-G0321-661.eventlog.json"
    assert identifiers.eventlog_filename == expected

def test_make_cdn_uri_from_uid_extension(identifiers):
    """Test generatie van een CDN URI."""
    uid = "NL-WbDRAZU-G0321-661-42"
    extension = "jpg"
    expected = "https://g0321.opslag.razu.nl/NL-WbDRAZU-G0321-661-42.jpg"
    assert identifiers.make_cdn_uri_from_uid_extension(uid, extension) == expected

def test_make_uri_prefix_from_kind(identifiers):
    """Test generatie van een URI prefix voor een specifiek type resource."""
    expected = "https://data.razu.nl/id/concept/NL-WbDRAZU-G0321-661"
    assert identifiers.make_uri_prefix_from_kind("concept") == expected

def test_make_uid_from_id(identifiers):
    """Test generatie van een UID van een object ID."""
    expected = "NL-WbDRAZU-G0321-661-42"
    assert identifiers.make_uid_from_id("42") == expected

def test_make_uri_from_id(identifiers):
    """Test generatie van een URI van een object ID."""
    expected = "https://data.razu.nl/id/object/NL-WbDRAZU-G0321-661-42"
    assert identifiers.make_uri_from_id("42") == expected

def test_make_uri_from_kind_uid(identifiers):
    """Test generatie van een URI van een type en UID."""
    uid = "NL-WbDRAZU-G0321-661-42"
    expected = "https://data.razu.nl/id/resource/NL-WbDRAZU-G0321-661-42"
    assert identifiers.make_uri_from_kind_uid("resource", uid) == expected

def test_make_filename_from_id(identifiers):
    """Test generatie van een bestandsnaam van een object ID."""
    expected = "NL-WbDRAZU-G0321-661-42.meta.json"
    assert identifiers.make_filename_from_id("42") == expected

def test_extract_id_from_identifier(identifiers):
    """Test extractie van een object ID uit een identifier."""
    identifier = "NL-WbDRAZU-G0321-661-42.meta.json"
    assert identifiers.extract_id_from_identifier(identifier) == "42"

def test_extract_parts_from_filename(identifiers):
    """Test extractie van verschillende delen uit een bestandsnaam."""
    filename = "NL-WbDRAZU-G0321-661-42.meta.json"
    
    assert identifiers.extract_source_id_from_filename(filename) == "G0321"
    assert identifiers.extract_archive_id_from_filename(filename) == "661"
    assert identifiers.extract_id_from_filename(filename) == "42"

def test_extract_id_from_file_path(identifiers):
    """Test extractie van een object ID uit een bestandspad."""
    path = "/some/path/to/NL-WbDRAZU-G0321-661-42.meta.json"
    assert identifiers.extract_id_from_file_path(path) == "42"
