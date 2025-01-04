import os
import sys
import json
from datetime import datetime

from razu.config import Config
from razu.identifiers import Identifiers
import razu.util as util

class Manifest:
    """
    A class to manage a manifest of files in a directory, ensuring that files are present 
    and checksums are correct. The manifest is stored as a JSON file that maps each file's 
    relative path to its MD5 checksum.
    """

    def __init__(self, save_directory):
        self.save_directory = save_directory
        self._cfg = Config.get_instance()
        self.files = {}
        self.is_valid = True
        self.is_modified = False

    @property
    def manifest_file_path(self):
        """Get the manifest file path. This is a property so it always uses the current config values."""
        self.id_factory = Identifiers(self._cfg)
        return os.path.join(self.save_directory, self.id_factory.manifest_filename)

    @classmethod
    def create_new(cls, save_directory) -> 'Manifest':
        """ Create a new manifest instance for a new manifest file. """
        manifest = cls(save_directory)
        manifest.is_valid = False  # No manifest yet, cannot be valid
        return manifest

    @classmethod
    def load_existing(cls, save_directory,  config=None) -> 'Manifest':
        """ Load an existing manifest file. """
        manifest = cls(save_directory)
        manifest_path = manifest.manifest_file_path
        
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found at '{manifest_path}'")
            
        manifest.load(manifest_path)
        manifest.is_valid = True
        return manifest

    def add_entry(self, file_path, md5hash, md5date):
        self.files[file_path] = {
            "MD5Hash": md5hash,
            "MD5HashDate": md5date
        }
        self.is_modified = True

    def get_filenames(self) -> list:
        return list(self.files.keys())

    def create_from_directory(self):
        """ Create a manifest by scanning all files in the directory. """
        if os.path.exists(self.manifest_file_path):
            raise FileExistsError(f"Manifest '{self.manifest_file_path}' already exists.")

        for root, dirs, files in os.walk(self.save_directory):
            for file in files:
                if file == os.path.basename(self.manifest_file_path):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.save_directory)
                self.add_entry(relative_path, util.calculate_md5(file_path), datetime.now().isoformat())
        self.is_modified = True
        self.save()
        self.is_valid = True
        print(f"Manifest created: {self.manifest_file_path}")

    def save(self):
        """ Save the manifest to a JSON file, but only if the manifest has been modified. """
        if self.is_modified:
            with open(self.manifest_file_path, "w") as json_file:
                json.dump(self.files, json_file, indent=4)
            self.is_modified = False

    def load(self, input_file):
        """ Load a manifest from a JSON file. """
        with open(input_file, "r") as json_file:
            self.files = json.load(json_file)
        self.is_modified = False

    def verify(self, ignore_missing=False, ignore_extra=False) -> dict:
        """
        Verify that all files listed in the manifest exist and have the correct checksums.
        Also, check if there are extra files in the directory that are not listed in the manifest.
        Raise an error if the manifest does not exist or if extra files are found.

        Args:
            ignore_missing (bool): If True, don't raise error for missing files.
            ignore_extra (bool): If True, don't raise error for extra files.

        Returns:
            dict: A dictionary of errors with keys 'missing_files', 'checksum_mismatch', and 'extra_files'.
        """
        errors = {
            "missing_files": [],
            "checksum_mismatch": [],
            "extra_files": []
        }

        # Verify files listed in the manifest
        for file_path, file_info in self.files.items():
            expected_checksum = file_info["MD5Hash"]
            absolute_path = os.path.join(self.save_directory, file_path)
            if not os.path.exists(absolute_path):
                errors["missing_files"].append(file_path)
            else:
                actual_checksum = util.calculate_md5(absolute_path)
                if actual_checksum != expected_checksum:
                    errors["checksum_mismatch"].append({
                        "file_path": file_path,
                        "expected_checksum": expected_checksum,
                        "actual_checksum": actual_checksum
                    })

        # Check for extra files in the directory
        for root, dirs, files in os.walk(self.save_directory):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), self.save_directory)
                if relative_path in {os.path.basename(self.manifest_file_path), self._cfg.eventlog_filename}:
                    continue
                if relative_path not in self.files:
                    errors["extra_files"].append(relative_path)

        if errors["checksum_mismatch"]:
            raise ValueError(f"Checksum mismatches: {errors['checksum_mismatch']}")

        if errors["missing_files"] and not ignore_missing:
            raise ValueError(f"Missing files: {errors['missing_files']}")

        if errors["extra_files"] and not ignore_extra:
            raise ValueError(f"Extra files found in the directory: {errors['extra_files']}")

        self.is_valid = True
        return errors

    def append(self):
        """
        Append missing files to the manifest by scanning the directory for files that
        are not yet listed in the manifest. Only files not already in the manifest will be added.

        Raises:
            FileNotFoundError: If the manifest file does not exist.
        """
        if not os.path.exists(self.manifest_file_path):
            raise FileNotFoundError(f"Manifest '{self.manifest_file_path}' does not exist.")

        self.load(self.manifest_file_path)

        for root, dirs, files in os.walk(self.save_directory):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), self.save_directory)
                if relative_path == os.path.basename(self.manifest_file_path):
                    continue
                if relative_path not in self.files:
                    file_path = os.path.join(self.save_directory, relative_path)
                    self.add_entry(relative_path, util.calculate_md5(file_path), datetime.now().isoformat())
                    self.is_modified = True

        if self.is_modified:
            self.save()
            print(f"Manifest '{self.manifest_file_path}' updated with missing files.")
        else:
            print("No missing files to append.")

    def extend_entry(self, file_path, additional_data):
        """
        Extend an existing file entry in the manifest by adding extra values to the dictionary.

        Args:
            file_path (str): The relative path to the file whose entry you want to update.
            additional_data (dict): A dictionary containing the additional data to add to the entry.

        Raises:
            KeyError: If the file entry does not exist in the manifest.
        """
        if file_path in self.files:
            self.files[file_path].update(additional_data)
            self.is_modified = True
        else:
            raise KeyError(f"File '{file_path}' does not exist in the manifest.")


if __name__ == "__main__":
    """
    Command-line interface for managing a file manifest.

    Usage:
        python manifest.py <directory> <manifest_file> <command>

    Commands:
        - create: Create a new manifest from the files in the directory. 
                  Raises an error if the manifest already exists.
        - verify: Verify the integrity of an existing manifest, checking for missing or extra files.
                  Raises an error if the manifest does not exist.
        - append: Append missing files to the manifest by scanning the directory for new files.
                  Raises an error if the manifest does not exist.
    """
    if len(sys.argv) < 3:
        print("Usage: python manifest.py <directory> <manifest_file> <command>")
        sys.exit(1)

    save_directory = sys.argv[1]
    manifest_file = sys.argv[2]
    command = sys.argv[3]

    manifest = Manifest(save_directory)

    if command == "create":
        try:
            manifest.create_from_directory()
        except FileExistsError as e:
            print(e)

    elif command == "verify":
        try:
            manifest.verify()
        except ValueError as e:
            print(e)

    elif command == "append":
        try:
            manifest.append()
        except ValueError as e:
            print(e)

    else:
        print("Unknown command. Use 'create', 'verify', or 'append'.")
