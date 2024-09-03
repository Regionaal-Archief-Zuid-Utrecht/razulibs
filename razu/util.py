from rdflib import Literal, XSD
import re

def date_type(value):
    """
    Converteert een string naar een RDF Literal met het juiste datatype als het een datum is.
    - "yyyy-mm-dd" -> xsd:date
    - "yyyy" -> xsd:gYear
    - Andere stringwaarden -> gewone Literal zonder datatype
    """
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    year_pattern = re.compile(r"^\d{4}$")

    if date_pattern.match(value):
        return Literal(value, datatype=XSD.date)
    elif year_pattern.match(value):
        return Literal(value, datatype=XSD.gYear)
    else:
        return Literal(value)
