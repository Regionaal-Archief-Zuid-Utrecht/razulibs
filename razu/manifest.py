import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from rdflib import RDF

from razu.config import Config
from razu.identifiers import Identifiers
from razu.meta_resource import StructuredMetaResource
from razu.meta_graph import MDTO
import razu.util as util

class ManifestEntry:
    """ Represents a single entry in the manifest, containing file metadata and checksum information."""

    def __init__(self, filename: str, md5hash: Optional[str] = None, md5date: Optional[str] = None, **kwargs):
        self.filename = filename
        self.md5hash = md5hash
        self.md5date = md5date
        self.metadata = kwargs  # For extra fields like ObjectUID, Source, etc.

    def update(self, **kwargs) -> None:
        if 'md5hash' in kwargs:
            self.md5hash = kwargs.pop('md5hash')
        if 'md5date' in kwargs:
            self.md5date = kwargs.pop('md5date')
        self.metadata.update(kwargs)

    def to_dict(self) -> dict:
        """Convert entry to dictionary for JSON serialization"""
        result = {
            'MD5Hash': self.md5hash,
            'MD5HashDate': self.md5date,
            **self.metadata
        }
        return result

    @classmethod
    def from_dict(cls, filename: str, data: dict) -> 'ManifestEntry':
        """Create manifest entry from dictionary"""
        md5hash = data.pop('MD5Hash', None)
        md5date = data.pop('MD5HashDate', None)
        return cls(filename, md5hash, md5date, **data)

    @classmethod
    def create_entry_for_metadata_resource(cls, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> 'ManifestEntry':
        """ Create a manifest entry for a StructuredMetaResource. """
        return cls(
                filename=resource.ext_filename,
                md5hash=resource.ext_file_md5checksum,
                md5date=resource.ext_file_checksum_datetime,
                ObjectUID=resource.uid,
                Source=archive_creator_uri,
                Dataset=dataset_id,
                FileFormat=resource.ext_file_fileformat_uri,
                OriginalFilename=resource.ext_file_original_filename,
                URI=resource.ext_file_uri
        )
        
    @classmethod
    def create_entry_for_referenced_resource(cls, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> 'ManifestEntry':
        """ Create a manifest entry for a file referenced by a StructuredMetaResource. """
        return cls(
            filename=resource.filename,
            md5hash=util.calculate_md5(resource.file_path),
            md5date=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            ObjectUID=resource.uid,
            Source=archive_creator_uri,
            Dataset=dataset_id,
            URI=resource.this_file_uri
        )




class Manifest:
    """
    A class to manage a manifest of files in a directory, ensuring that files are present 
    and checksums are correct. The manifest is stored as a JSON file that maps each file's 
    relative path to its metadata and checksum information.
    """

    def __init__(self, save_directory: str):
        self.save_directory = save_directory
        self._cfg = Config.get_instance()
        self.entries: Dict[str, ManifestEntry] = {}
        self.manifest_filename = None  # Will be set by create_new or load_existing
        self.is_valid = True
        self.is_modified = False

    @property
    def manifest_file_path(self) -> str:
        """Get the manifest file path. Uses explicit filename if set, otherwise generates from id_factory."""
        if self.manifest_filename is None:
            # Only create id_factory when we need to generate the filename
            id_factory = Identifiers(self._cfg)
            return os.path.join(self.save_directory, id_factory.manifest_filename)
        return os.path.join(self.save_directory, self.manifest_filename)

    @classmethod
    def create_new(cls, save_directory: str) -> 'Manifest':
        """Create a new manifest instance for a new manifest file."""
        manifest = cls(save_directory)
        # For new manifests, we always need the id_factory
        id_factory = Identifiers(manifest._cfg)
        manifest.manifest_filename = id_factory.manifest_filename
        manifest.is_valid = False  # No manifest yet, cannot be valid
        return manifest

    @classmethod
    def load_existing(cls, save_directory: str, manifest_filename: str = None) -> 'Manifest':
        """Load an existing manifest file.
        
        Args:
            save_directory: Directory containing the manifest
            manifest_filename: Optional explicit manifest filename. If not provided, uses id_factory to generate name.
        """
        manifest = cls(save_directory)
        manifest.manifest_filename = manifest_filename
        manifest_path = manifest.manifest_file_path
        
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found at '{manifest_path}'")
            
        manifest.load(manifest_path)
        manifest.is_valid = True
        return manifest

    def add_entry(self, filename: str, **kwargs) -> ManifestEntry:
        """Add or update a manifest entry with metadata and checksum information"""
        entry = ManifestEntry(filename, **kwargs)
        self.entries[filename] = entry
        self.is_modified = True
        return entry

    def add_metadata_resource(self, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> ManifestEntry:
        """Add a resource to the manifest"""
        entry = ManifestEntry.create_entry_for_metadata_resource(resource, archive_creator_uri, dataset_id)
        self.entries[entry.filename] = entry
        self.is_modified = True
        return entry

    def add_referenced_resource(self, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> ManifestEntry:
        """Add a resource to the manifest"""
        entry = ManifestEntry.create_entry_for_referenced_resource(resource, archive_creator_uri, dataset_id)
        self.entries[entry.filename] = entry
        self.is_modified = True
        return entry

    def update_entry(self, filename: str, **kwargs) -> None:
        """Update an existing entry's metadata and/or checksum information"""
        if filename not in self.entries:
            raise KeyError(f"No entry found for {filename}")
        self.entries[filename].update(**kwargs)
        self.is_modified = True

    def get_entry(self, filename: str) -> Optional[ManifestEntry]:
        """Get a manifest entry by filename"""
        return self.entries.get(filename)

    def get_filenames(self) -> List[str]:
        """Get list of all filenames in the manifest"""
        return list(self.entries.keys())

    def save(self) -> None:
        """Save the manifest to a JSON file, but only if the manifest has been modified."""
        if self.is_modified:
            entries_dict = {
                filename: entry.to_dict() 
                for filename, entry in self.entries.items()
            }
            with open(self.manifest_file_path, "w") as json_file:
                json.dump(entries_dict, json_file, indent=4)
            self.is_modified = False

    def load(self, input_file: str) -> None:
        """Load a manifest from a JSON file."""
        with open(input_file, "r") as json_file:
            entries_dict = json.load(json_file)
            self.entries = {
                filename: ManifestEntry.from_dict(filename, data)
                for filename, data in entries_dict.items()
            }
        self.is_modified = False

    def validate(self, ignore_files: list = None) -> dict:
        """ Verify 1 to 1 relationship between manifest entries and files in the directory. 

        Args:
            ignore_files: Optional list of filenames to ignore when checking for extra files.
                         The manifest file itself is always ignored.

        Returns:
            dict: A dictionary of errors with keys 'missing_files', 'checksum_mismatch', and 'extra_files'
        """
        errors = {
            'missing_files': [],
            'checksum_mismatch': [],
            'extra_files': []
        }

        ignore_files = ignore_files or []
        ignore_files.append(os.path.basename(self.manifest_file_path))

        # Check manifest entries against filesystem
        for filename in self.entries:
            file_path = os.path.join(self.save_directory, filename)
            if not os.path.exists(file_path):
                errors['missing_files'].append(filename)
            else:
                current_md5 = util.calculate_md5(file_path)
                if current_md5 != self.entries[filename].md5hash:
                    errors['checksum_mismatch'].append(filename)

        # Check filesystem against manifest entries
        for root, dirs, files in os.walk(self.save_directory):
            for file in files:
                if file in ignore_files:
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.save_directory)
                if relative_path not in self.entries:
                    errors['extra_files'].append(relative_path)

        if errors['missing_files']:
            raise FileNotFoundError(f"Files missing: {errors['missing_files']}")
        if errors['extra_files']:
            raise FileExistsError(f"Extra files found: {errors['extra_files']}")
        return errors


if __name__ == "__main__":
    """Command-line interface for managing a file manifest."""
    if len(sys.argv) < 3:
        print("Usage: python manifest.py <directory> <manifest-file> [files-to-ignore ...]")
        print("\nExample:")
        print("  python manifest.py sip NL-WbDRAZU-G0321-661.manifest.json eventlog.json metadata.json")
        sys.exit(1)

    directory = sys.argv[1]
    manifest_filename = sys.argv[2]
    ignore_files = sys.argv[3:] if len(sys.argv) > 3 else None

    try:
        manifest = Manifest.load_existing(directory, manifest_filename=manifest_filename)
        errors = manifest.validate(ignore_files=ignore_files)
        if any(errors.values()):
            print("Verification failed:")
            for error_type, files in errors.items():
                if files:
                    print(f"{error_type}: {files}")
        else:
            print(f"Directory {directory} complies with manifest {manifest_filename} and validated successfully.")
            if ignore_files:
                print(f"Note: The following files were ignored during validation: {', '.join(ignore_files)}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
