import json
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


def test_validate_with_filename_prefix(manifest_setup):
    """Validation should support a filename prefix that is not part of the local path."""
    manifest, tmp_path = manifest_setup
    manifest_path = Path(manifest.manifest_file_path)
    data = json.loads(manifest_path.read_text())
    prefix = "nl-wbdrazu/k50907905/689/"
    prefixed = {f"{prefix}{k}": v for k, v in data.items()}
    manifest_path.write_text(json.dumps(prefixed))
    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate(filename_prefix=prefix)
    assert not errors['missing_files']
    assert not errors['checksum_mismatch']
    assert not errors['extra_files']


def test_validate_extra_file_with_filename_prefix(manifest_setup):
    """Extra files should be reported with the logical prefixed path."""
    manifest, tmp_path = manifest_setup
    manifest_path = Path(manifest.manifest_file_path)
    data = json.loads(manifest_path.read_text())
    prefix = "nl-wbdrazu/k50907905/689/"
    prefixed = {f"{prefix}{k}": v for k, v in data.items()}
    manifest_path.write_text(json.dumps(prefixed))
    (tmp_path / 'extra.txt').write_text('extra')
    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate(filename_prefix=prefix)
    assert f"{prefix}extra.txt" in errors['extra_files']


def test_validate_missing_file_with_filename_prefix(manifest_setup):
    """Missing files should be reported with the manifest key including prefix."""
    manifest, tmp_path = manifest_setup
    manifest_path = Path(manifest.manifest_file_path)
    data = json.loads(manifest_path.read_text())
    prefix = "nl-wbdrazu/k50907905/689/"
    prefixed = {f"{prefix}{k}": v for k, v in data.items()}
    manifest_path.write_text(json.dumps(prefixed))
    (tmp_path / 'a.txt').unlink()
    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate(filename_prefix=prefix)
    assert f"{prefix}a.txt" in errors['missing_files']


def test_create_with_filename_prefix(config, tmp_path):
    """Creating a manifest with a filename prefix should prepend it to all entry keys."""
    (tmp_path / 'a.txt').write_text('A')
    (tmp_path / 'b.txt').write_text('BB')
    subdir = tmp_path / 'subdir'
    subdir.mkdir()
    (subdir / 'c.txt').write_text('CCC')

    prefix = "nl-wbdrazu/k50907905/689/"
    manifest = Manifest.create_from_directory(str(tmp_path), filename_prefix=prefix)
    assert f"{prefix}a.txt" in manifest.entries
    assert f"{prefix}subdir/c.txt" in manifest.entries


def test_create_validate_with_filename_prefix(config, tmp_path):
    """A manifest created with a filename prefix should validate with the same prefix."""
    (tmp_path / 'a.txt').write_text('A')
    (tmp_path / 'b.txt').write_text('BB')

    prefix = "archive/123/"
    manifest = Manifest.create_from_directory(str(tmp_path), filename_prefix=prefix)
    manifest.save()

    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate(filename_prefix=prefix)
    assert not errors['missing_files']
    assert not errors['checksum_mismatch']
    assert not errors['extra_files']


def test_create_validate_without_filename_prefix_fails(config, tmp_path):
    """A manifest created with a filename prefix should not validate without the prefix."""
    (tmp_path / 'a.txt').write_text('A')
    (tmp_path / 'b.txt').write_text('BB')

    prefix = "archive/123/"
    manifest = Manifest.create_from_directory(str(tmp_path), filename_prefix=prefix)
    manifest.save()

    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate()
    assert errors['missing_files'] or errors['extra_files']


def test_create_validate_with_different_filename_prefix_fails(config, tmp_path):
    """A manifest created with a filename prefix should not validate with a different prefix."""
    (tmp_path / 'a.txt').write_text('A')
    (tmp_path / 'b.txt').write_text('BB')

    prefix = "archive/123/"
    manifest = Manifest.create_from_directory(str(tmp_path), filename_prefix=prefix)
    manifest.save()

    loaded = Manifest.load_existing(str(tmp_path), manifest_filename='manifest.json')
    errors = loaded.validate(filename_prefix="other/")
    assert errors['missing_files'] or errors['extra_files']
