import re
import os
import hashlib

from rdflib import Literal, XSD
from datetime import datetime
from razu.config import Config

def date_type(datestring: str) -> Literal:
    """
    Converts a string into an RDF Literal with the appropriate datatype if it represents a date.
    - "yyyy-mm-dd" -> "yyyy-mm-dd"^^xsd:date
    - "yyyy" -> "yyyy-mm-dd"^^xsd:gYear
    - "d{1,2}-d{1,2}-d{4}" -> "yyyy-mm-dd"^^xsd:date
    - Other string values -> Literal without a specific datatype
    """
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    year_pattern = re.compile(r"^\d{4}$")
    day_month_year_pattern = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")

    if date_pattern.match(datestring):
        return Literal(datestring, datatype=XSD.date)
    elif year_pattern.match(datestring):
        return Literal(datestring, datatype=XSD.gYear)
    elif day_month_year_pattern.match(datestring):
        day, month, year = day_month_year_pattern.match(datestring).groups()
        formatted_date = f"{year}-{int(month):02d}-{int(day):02d}"
        return Literal(formatted_date, datatype=XSD.date)
    else:
        return Literal(datestring)

def get_full_extension(filename: str) -> str:
    """
    Returns the full extension of the given filename, including any intermediate extensions.
    
    Parameters:
    -----------
    filename : str
        The input filename.

    Returns:
    --------
    str
        The full extension, including multiple parts if they exist (e.g., ".tar.gz").
    """
    name, ext = os.path.splitext(filename)
    full_ext = ext

    while ext:
        name, ext = os.path.splitext(name)
        full_ext = ext + full_ext if ext else full_ext

    return full_ext

def get_last_modified(file_path: str) -> str:
    """
    Retrieves the last modified timestamp of a file as an ISO 8601 formatted string.

    Parameters:
    -----------
    file_path : str
        Path to the file whose last modified time is needed.

    Returns:
    --------
    str
        ISO 8601 formatted timestamp of the last modification date.
    """
    timestamp = os.path.getmtime(file_path)
    last_modified_date = datetime.fromtimestamp(timestamp)
    return last_modified_date.strftime("%Y-%m-%dT%H:%M:%S")

def extract_part_from_filename(filename: str, part_number: int) -> str:
    """
    Extracts a specific part of the filename based on its position after cfg.razu_file_id.
    
    Parameters:
    -----------
    filename : str
        The input filename.
    part_number : int
        The part of the filename to extract (1-based index).

    Returns:
    --------
    str
        The extracted part of the filename.

    Raises:
    -------
    ValueError:
        If the razu file ID or the desired part is not found.
    """
    cfg = Config.get_instance()

    start_index = filename.find(cfg.razu_file_id)
    if start_index == -1:
        raise ValueError(f"razu file ID '{cfg.razu_file_id}' not found in the filename.")
    start_index += len(cfg.razu_file_id) + 1  
    for _ in range(part_number - 1):
        start_index = filename.find('-', start_index) + 1
        if start_index == 0:
            raise ValueError(f"Part {part_number} not found in the filename.")
    end_index = filename.find('-', start_index)
    if end_index == -1:
        return filename[start_index:]
    return filename[start_index:end_index]

def filename_without_extensions(filename: str) -> str:
    """
    Returns the filename without any extensions, removing everything after the first dot.

    Parameters:
    -----------
    filename : str
        The input filename.

    Returns:
    --------
    str
        The filename without the extensions.
    """
    dot_index = filename.find('.')
    if dot_index == -1:
        return filename
    return filename[:dot_index]

def normalize_path(file_path, base_dir=None):
    """Normalize a path to be relative with forward slashes.
    
    Args:
        file_path: The path to normalize (can be absolute or relative, with any path separator)
        base_dir: Optional base directory to make the path relative to. If None,
                 looks for 'bestanden' in the path and takes everything after it.
    Returns:
        A normalized path using forward slashes
    """
    # Convert all separators to forward slashes
    file_path = file_path.replace('\\', '/')
    
    if base_dir:
        # If base_dir is provided, make path relative to it
        base_dir = base_dir.replace('\\', '/')
        if file_path.startswith(base_dir):
            return file_path[len(base_dir):].lstrip('/')
    
    # Find 'bestanden' in the path and take everything after it
    parts = file_path.split('/')
    try:
        idx = parts.index('bestanden')
        return '/'.join(parts[idx + 1:])
    except ValueError:
        return file_path.replace('\\', '/')

def calculate_md5(file_path):
    """
    Calculate the MD5 checksum of a file.
    """
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            md5.update(chunk)
    return md5.hexdigest()
