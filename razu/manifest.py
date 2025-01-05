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
    """
    Represents a single entry in the manifest, containing file metadata and checksum information.
    """
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
    def from_resource(cls, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> 'ManifestEntry':
        """ Create a manifest entry from a StructuredMetaResource. """
        is_MDTO_bestand = (resource.uri, RDF.type, MDTO.Bestand) in resource.graph
        if is_MDTO_bestand:
            return cls(
                resource.ext_filename,
                md5hash=resource.ext_file_md5checksum,
                md5date=resource.ext_file_checksum_datetime,
                ObjectUID=resource.uid,
                Source=archive_creator_uri,
                Dataset=dataset_id,
                FileFormat=resource.ext_file_fileformat_uri,
                OriginalFilename=resource.ext_file_original_filename,
                URI=resource.ext_file_uri
            )
        else:
            return cls(
                resource.filename,
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
        self.is_valid = True
        self.is_modified = False

    @property
    def manifest_file_path(self) -> str:
        """Get the manifest file path. This is a property so it always uses the current config values."""
        self.id_factory = Identifiers(self._cfg)
        return os.path.join(self.save_directory, self.id_factory.manifest_filename)

    @classmethod
    def create_new(cls, save_directory: str) -> 'Manifest':
        """Create a new manifest instance for a new manifest file."""
        manifest = cls(save_directory)
        manifest.is_valid = False  # No manifest yet, cannot be valid
        return manifest

    @classmethod
    def load_existing(cls, save_directory: str, config=None) -> 'Manifest':
        """Load an existing manifest file."""
        manifest = cls(save_directory)
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

    def add_resource(self, resource: StructuredMetaResource, archive_creator_uri: str, dataset_id: str) -> ManifestEntry:
        """Add a resource to the manifest"""
        entry = ManifestEntry.from_resource(resource, archive_creator_uri, dataset_id)
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

    def create_from_directory(self) -> None:
        """Create a manifest by scanning all files in the directory."""
        if os.path.exists(self.manifest_file_path):
            raise FileExistsError(f"Manifest '{self.manifest_file_path}' already exists.")
        for root, dirs, files in os.walk(self.save_directory):
            for file in files:
                if file == os.path.basename(self.manifest_file_path):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.save_directory)
                self.add_entry(
                    relative_path,
                    md5hash=util.calculate_md5(file_path),
                    md5date=datetime.now().isoformat()
                )
        self.save()
        self.is_valid = True
        print(f"Manifest created: {self.manifest_file_path}")

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

    def verify(self, ignore_missing: bool = False, ignore_extra: bool = False) -> dict:
        """
        Verify that all files listed in the manifest exist and have the correct checksums.
        Also, check if there are extra files in the directory that are not listed in the manifest.

        Args:
            ignore_missing: If True, don't raise error for missing files
            ignore_extra: If True, don't raise error for extra files

        Returns:
            dict: A dictionary of errors with keys 'missing_files', 'checksum_mismatch', and 'extra_files'
        """
        errors = {
            'missing_files': [],
            'checksum_mismatch': [],
            'extra_files': []
        }

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
                if file == os.path.basename(self.manifest_file_path):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.save_directory)
                if relative_path not in self.entries:
                    errors['extra_files'].append(relative_path)

        if not ignore_missing and errors['missing_files']:
            raise FileNotFoundError(f"Files missing: {errors['missing_files']}")
        if not ignore_extra and errors['extra_files']:
            raise FileExistsError(f"Extra files found: {errors['extra_files']}")

        return errors


if __name__ == "__main__":
    """Command-line interface for managing a file manifest."""
    if len(sys.argv) < 3:
        print("Usage: python manifest.py <command> <directory> [--ignore-missing] [--ignore-extra]")
        print("Commands:")
        print("  create  - Create a new manifest for the directory")
        print("  verify  - Verify files against existing manifest")
        sys.exit(1)

    command = sys.argv[1]
    directory = sys.argv[2]
    ignore_missing = "--ignore-missing" in sys.argv
    ignore_extra = "--ignore-extra" in sys.argv

    try:
        if command == "create":
            manifest = Manifest.create_new(directory)
            manifest.create_from_directory()
        elif command == "verify":
            manifest = Manifest.load_existing(directory)
            errors = manifest.verify(ignore_missing, ignore_extra)
            if any(errors.values()):
                print("Verification failed:")
                for error_type, files in errors.items():
                    if files:
                        print(f"{error_type}: {files}")
            else:
                print("Verification successful")
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
