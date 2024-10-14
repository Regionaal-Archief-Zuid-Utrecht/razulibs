import os
import sys
import hashlib
import json
from datetime import datetime

import razu.util as util


class Manifest:
    """
    A class to manage a manifest of files in a directory, ensuring that files are present 
    and checksums are correct. The manifest is stored as a JSON file that maps each file's 
    relative path to its MD5 checksum.

    This class provides functionality to:
    - Create a manifest from all files in a directory.
    - Load an existing manifest and verify its integrity against the current directory structure.
    - Append missing files to the manifest if it already exists.
    - Save the manifest to a JSON file only if changes were made.
    - Update an existing file entry in the manifest by adding extra values to the dictionary

    Attributes:
        directory (str): The directory being managed by the manifest.
        manifest_file (str): The path to the JSON manifest file.
        files (dict): A dictionary that stores relative file paths and their MD5 checksums.
        is_valid (bool): Indicates if the manifest is valid after verification.
        modified (bool): Indicates if the manifest has been modified since it was loaded or created.
    """
    
    def __init__(self, manifest_directory, manifest_file):
        """
        Initialize the Manifest object. 
        Load an existing manifest file or mark the manifest as invalid if the file does not exist.

        Args:
            manifest_directory (str): The directory to scan for files.
            manifest_file (str): The name of the manifest file.
        """
        self.directory = manifest_directory
        self.manifest_file = os.path.join(manifest_directory, manifest_file)
        self.files = {}
        self.is_valid = True
        self.modified = False
        self.newest_id = 0 

        # Load existing manifest or mark as invalid
        if os.path.exists(self.manifest_file):
            self.load(self.manifest_file)
        else:
            self.is_valid = False  # No manifest yet, cannot be valid

    def add_entry(self, file_path, md5hash, md5date):
        self.files[file_path] =  {
            "MD5Hash": md5hash,
            "MD5HashDate": md5date
        }
        self.modified = True

    def get_filenames(self) -> list:
        return list(self.files.keys()) 

    def create_from_directory(self):
        """
        Create a manifest by scanning all files in the directory, 
        excluding the manifest file itself.

        Raises:
            FileExistsError: If the manifest file already exists.
        """
        if os.path.exists(self.manifest_file):
            raise FileExistsError(f"Manifest '{self.manifest_file}' already exists.")
        
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file == os.path.basename(self.manifest_file):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.directory)
                self.add_entry(relative_path, self.calculate_md5(file_path), datetime.now().isoformat())
        self.modified = True
        self.save()
        print(f"Manifest created: {self.manifest_file}")

    @staticmethod
    def calculate_md5(file_path):
        """
        Calculate the MD5 checksum of a file.
        """
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                md5.update(chunk)
        return md5.hexdigest()

    def save(self):
        """
        Save the manifest to a JSON file, but only if the manifest has been modified.
        """
        if self.modified:
            with open(self.manifest_file, "w") as json_file:
                json.dump(self.files, json_file, indent=4)
            self.modified = False

    def load(self, input_file):
        """
        Load a manifest from a JSON file.

        Args:
            input_file (str): The path to the manifest file.
        """
        with open(input_file, "r") as json_file:
            self.files = json.load(json_file)

        for filename in self.files.keys():
            id = util.extract_id_from_filename(filename)
            if id is not None:
                if id > self.newest_id:
                    self.newest_id = id

        self.modified = False

    def verify(self, ignore_missing=False, ignore_extra=False):
        """
        Verify that all files listed in the manifest exist and have the correct checksums.
        Also, check if there are extra files in the directory that are not listed in the manifest.
        Raise an error if the manifest does not exist or if extra files are found.

        Raises:
            FileNotFoundError: If the manifest file does not exist.
            Warning: If extra files are found in the directory that are not in the manifest.

        Returns:
            dict: A dictionary of errors with keys 'missing_files', 'checksum_mismatch', and 'extra_files'.
        """
        if not os.path.exists(self.manifest_file):
            raise FileNotFoundError(f"Manifest '{self.manifest_file}' does not exist. Please create a manifest first.")

        errors = {
            "missing_files": [],
            "checksum_mismatch": [],
            "extra_files": []
        }

        # Verify files listed in the manifest
        for file_path, file_info in self.files.items():
            expected_checksum = file_info["MD5Hash"]
            absolute_path = os.path.join(self.directory, file_path)
            if not os.path.exists(absolute_path):
                errors["missing_files"].append(file_path)
            else:
                actual_checksum = self.calculate_md5(absolute_path)
                if actual_checksum != expected_checksum:
                    errors["checksum_mismatch"].append({
                        "file_path": file_path,
                        "expected_checksum": expected_checksum,
                        "actual_checksum": actual_checksum
                    })

        # Check for extra files in the directory
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), self.directory)
                if relative_path == os.path.basename(self.manifest_file):
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
        return
    
    
    def append(self):
        """
        Append missing files to the manifest by scanning the directory for files that
        are not yet listed in the manifest. Only files not already in the manifest will be added.

        Raises:
            FileNotFoundError: If the manifest file does not exist.
        """
        if not os.path.exists(self.manifest_file):
            raise FileNotFoundError(f"Manifest '{self.manifest_file}' does not exist.")

        self.load(self.manifest_file)

        for root, dirs, files in os.walk(self.directory):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), self.directory)
                if relative_path == os.path.basename(self.manifest_file):
                    continue
                if relative_path not in self.files:
                    file_path = os.path.join(self.directory, relative_path)
                    self.add_entry(relative_path, self.calculate_md5(file_path), datetime.now().isoformat())
                    self.modified = True

        if self.modified:
            self.save()
            print(f"Manifest '{self.manifest_file}' updated with missing files.")
        else:
            print("No missing files to append.")

    def update_entry(self, file_path, additional_data):
        """
        Update an existing file entry in the manifest by adding extra values to the dictionary.

        Args:
            file_path (str): The relative path to the file whose entry you want to update.
            additional_data (dict): A dictionary containing the additional data to add to the entry.

        Raises:
            KeyError: If the file entry does not exist in the manifest.
        """
        if file_path in self.files:
            self.files[file_path].update(additional_data)  # Update the existing entry with new data
            self.modified = True
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

    directory = sys.argv[1]
    manifest_file = sys.argv[2]
    command = sys.argv[3]

    manifest = Manifest(directory, manifest_file)

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
