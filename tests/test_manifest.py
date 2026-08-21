import pytest
from pathlib import Path
from razu.config import Config
from razu.manifest import Manifest


@pytest.fixture
def test_config_path():
    """Return the path to the test configuration file."""
    return str(Path(__file__).parent / 'fixtures' / 'test_identifiers.yaml')


@pytest.fixture
def config(test_config_path):
    """Initialize a fresh Config instance for manifest tests."""
    Config.reset()
    cfg = Config.initialize(config_file=test_config_path)
    yield cfg
    Config.reset()


@pytest.fixture
def manifest_setup(config, tmp_path):
    """Create a temporary directory with files and a saved manifest."""
    (tmp_path / 'a.txt').write_text('A')
    (tmp_path / 'b.txt').write_text('BB')
    subdir = tmp_path / 'subdir'
    subdir.mkdir()
    (subdir / 'c.txt').write_text('CCC')

    manifest = Manifest.create_from_directory(str(tmp_path))
    manifest.save()
    return manifest, tmp_path


def test_create_manifest_no_errors(manifest_setup):
    """Creating a manifest should succeed without errors."""
    manifest, tmp_path = manifest_setup
    assert manifest.is_valid
    assert len(manifest.entries) == 3
    assert Path(manifest.manifest_file_path).exists()


def test_create_manifest_without_metadata(manifest_setup):
    """Creating a manifest should not include FileSize, LastModified or FileExtension."""
    manifest, tmp_path = manifest_setup
    for entry in manifest.entries.values():
        assert 'FileSize' not in entry.metadata
        assert 'LastModified' not in entry.metadata
        assert 'FileExtension' not in entry.metadata


def test_validate_created_manifest(manifest_setup):
    """A freshly created manifest should validate without errors."""
    manifest, tmp_path = manifest_setup
    errors = manifest.validate()
    assert not errors['missing_files']
    assert not errors['checksum_mismatch']
    assert not errors['extra_files']


def test_validate_extra_file_fails(manifest_setup):
    """Adding a file after creating the manifest should produce an extra_files error."""
    manifest, tmp_path = manifest_setup
    (tmp_path / 'extra.txt').write_text('extra')
    errors = manifest.validate()
    assert 'extra.txt' in errors['extra_files']


def test_validate_missing_file_fails(manifest_setup):
    """Removing a file after creating the manifest should produce a missing_files error."""
    manifest, tmp_path = manifest_setup
    (tmp_path / 'a.txt').unlink()
    errors = manifest.validate()
    assert 'a.txt' in errors['missing_files']


def test_validate_checksum_mismatch_fails(manifest_setup):
    """Modifying a file after creating the manifest should produce a checksum_mismatch error."""
    manifest, tmp_path = manifest_setup
    (tmp_path / 'a.txt').write_text('modified')
    errors = manifest.validate()
    assert 'a.txt' in errors['checksum_mismatch']
