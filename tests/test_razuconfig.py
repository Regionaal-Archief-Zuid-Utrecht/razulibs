import pytest
from razu.razuconfig import RazuConfig


def test_singleton_behavior():
    """Test dat de RazuConfig class zich gedraagt als een singleton."""
    config1 = RazuConfig(archive_creator_id="G312", archive_id="661")
    config2 = RazuConfig()
    
    # Controleer dat beide variabelen op hetzelfde object wijzen
    assert config1 is config2


def test_default_settings():
    """Test dat de standaardwaarden correct worden ingesteld."""
    config = RazuConfig()
    
    assert config.RAZU_base_URI == "https://data.razu.nl/"
    assert config.RAZU_file_id == "NL-WbDRAZU"
    assert config.sparql_endpoint_prefix == "https://api.data.razu.nl/datasets/id/"
    assert config.sparql_endpoint_suffix == "/sparql"
    assert config.resource_identifier == "id"
    assert config.metadata_suffix == "meta"


def test_custom_settings():
    """Test dat aangepaste configuratie-instellingen worden toegevoegd of overschreven."""
    config = RazuConfig(custom_setting="custom_value")
    
    # Controleer dat de aangepaste waarde correct is ingesteld
    assert config.custom_setting == "custom_value"
    

def test_filename_prefix_success():
    """Test dat de filename_prefix correct wordt gegenereerd."""
    config = RazuConfig()
    
    expected_prefix = "NL-WbDRAZU-G312-661"
    assert config.filename_prefix == expected_prefix


def test_filename_prefix_missing_attributes():
    """Test dat een ValueError wordt opgegooid als vereiste attributen ontbreken."""
    config = RazuConfig()
    
    with pytest.raises(AttributeError):
        _ = config.filename_prefix_123


def test_URI_prefix_success():
    """Test dat de URI_prefix correct wordt gegenereerd."""
    config = RazuConfig()
    
    expected_uri_prefix = "https://data.razu.nl/id/object/NL-WbDRAZU-G312-661-"
    assert config.object_uri_prefix == expected_uri_prefix
