from rdflib import Literal, XSD
import re

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
