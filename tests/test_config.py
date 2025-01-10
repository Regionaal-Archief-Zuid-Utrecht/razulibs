import os
import pytest
from pathlib import Path
from razu.config import Config

@pytest.fixture
def test_config_path():
    """Return the path to the test configuration file."""
    return str(Path(__file__).parent / 'fixtures' / 'test_config.yaml')

@pytest.fixture
def config(test_config_path):
    """Create a Config instance with test configuration."""
    Config.reset()  # Reset any existing configuration
    return Config.initialize(config_file=test_config_path)

def test_config_loads_test_values(config):
    """Test that configuration values are loaded correctly from test YAML."""
    assert config.razu_base_uri == "https://data.razu.nl/"
    assert config.resource_identifier_segment == "id"
    assert config.default_entity_kind_segment == "object"
    assert config.razu_file_id == "NL-WbDRAZU"

def test_singleton_behavior(config):
    """Test that Config class behaves as a singleton."""
    config2 = Config.get_instance()
    assert config is config2

def test_config_immutability(config):
    """Test that configuration values cannot be modified after loading."""
    with pytest.raises(ValueError):
        config.razu_base_uri = "new-value"

def test_missing_attribute(config):
    """Test that accessing a non-existent configuration raises AttributeError."""
    with pytest.raises(AttributeError):
        _ = config.non_existent_setting

def test_all_required_settings_present(config):
    """Test that all required configuration settings are present."""
    required_settings = [
        'razu_base_uri',
        'resource_identifier_segment',
        'default_entity_kind_segment',
        'razu_file_id',
        'metadata_suffix',
        'manifest_suffix',
        'eventlog_suffix',
        'metadata_extension',
        'storage_base_domain',
        'sparql_endpoint_prefix',
        'sparql_endpoint_suffix',
        'default_resources_directory',
        'default_metadata_directory',
        'default_sip_directory',
        'default_av_executable',
        'default_droid_executable'
    ]
    
    for setting in required_settings:
        assert hasattr(config, setting), f"Missing required setting: {setting}"
