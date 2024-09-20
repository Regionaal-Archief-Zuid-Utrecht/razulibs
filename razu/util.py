import re
import os
from rdflib import Literal, XSD
from datetime import datetime


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
    name, ext = os.path.splitext(filename)
    full_ext = ext
    
    while ext:
        name, ext = os.path.splitext(name)
        full_ext = ext + full_ext if ext else full_ext
    
    return full_ext

def get_last_modified(file_path: str) -> str:
    timestamp = os.path.getmtime(file_path)
    last_modified_date = datetime.fromtimestamp(timestamp)
    return last_modified_date.strftime("%Y-%m-%dT%H:%M:%S")