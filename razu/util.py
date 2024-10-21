import re
import os


from rdflib import Literal, XSD
from datetime import datetime
from razuconfig import RazuConfig


def date_type(datestring: str) -> Literal:
    """
    Converts a string into an RDF Literal with the appropriate datatype if it represents a date.
    - "yyyy-mm-dd" -> "yyyy-mm-dd"^^xsd:date
    - "yyyy" -> "yyyy-mm-dd"^^xsd:gYear
    - Other string values -> Literal without a specific datatype

    Parameters:
    -----------
    datestring : str
        The string to be converted into a typed Literal.

    Returns:
    --------
    rdflib.Literal
        An RDF Literal with the appropriate datatype, if applicable.
    """
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    year_pattern = re.compile(r"^\d{4}$")

    if date_pattern.match(datestring):
        return Literal(datestring, datatype=XSD.date)
    elif year_pattern.match(datestring):
        return Literal(datestring, datatype=XSD.gYear)
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
    Extracts a specific part of the filename based on its position after cfg.RAZU_file_id.
    
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
        If the RAZU file ID or the desired part is not found.
    """
    cfg = RazuConfig()

    start_index = filename.find(cfg.RAZU_file_id)
    if start_index == -1:
        raise ValueError(f"RAZU file ID '{cfg.RAZU_file_id}' not found in the filename.")
    start_index += len(cfg.RAZU_file_id) + 1  
    for _ in range(part_number - 1):
        start_index = filename.find('-', start_index) + 1
        if start_index == 0:
            raise ValueError(f"Part {part_number} not found in the filename.")
    end_index = filename.find('-', start_index)
    if end_index == -1:
        return filename[start_index:]
    return filename[start_index:end_index]


def extract_source_from_filename(filename: str) -> str:
    """
    Extracts the "source" part of the filename that comes after cfg.RAZU_file_id.

    Parameters:
    -----------
    filename : str
        The input filename.

    Returns:
    --------
    str
        The extracted source part of the filename.
    """
    return extract_part_from_filename(filename, 1)


def extract_archive_from_filename(filename: str) -> str:
    """
    Extracts the "archive" part of the filename that comes after cfg.RAZU_file_id and the source part.

    Parameters:
    -----------
    filename : str
        The input filename.

    Returns:
    --------
    str
        The extracted archive part of the filename.
    """
    return extract_part_from_filename(filename, 2)


def extract_id_from_filename(filename: str):
    part = extract_part_from_filename(filename, 3)
    if part:
        part = part.split('.')[0]
    try:
        return int(part)
    except (ValueError, TypeError):
        return None 


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
