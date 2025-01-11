import pytest
from razu.util import normalize_path, date_type
from rdflib import Literal, XSD
from datetime import date

def test_normalize_path_with_windows_path():
    """Test normalisatie van Windows pad met backslashes."""
    input_path = r"C:\Users\test\bestanden\subfolder\file.txt"
    expected = "subfolder/file.txt"
    assert normalize_path(input_path) == expected

def test_normalize_path_with_unix_path():
    """Test normalisatie van Unix pad met forward slashes."""
    input_path = "/home/user/bestanden/subfolder/file.txt"
    expected = "subfolder/file.txt"
    assert normalize_path(input_path) == expected

def test_normalize_path_with_base_dir():
    """Test normalisatie met expliciete base_dir."""
    input_path = "/home/user/project/data/file.txt"
    base_dir = "/home/user/project"
    expected = "data/file.txt"
    assert normalize_path(input_path, base_dir) == expected

def test_normalize_path_with_base_dir_windows():
    """Test normalisatie met expliciete base_dir in Windows formaat."""
    input_path = r"C:\Users\test\project\data\file.txt"
    base_dir = r"C:\Users\test\project"
    expected = "data/file.txt"
    assert normalize_path(input_path, base_dir) == expected

def test_normalize_path_no_bestanden():
    """Test gedrag wanneer 'bestanden' niet in het pad voorkomt."""
    input_path = "/home/user/documents/file.txt"
    expected = "/home/user/documents/file.txt"
    assert normalize_path(input_path) == expected

def test_normalize_path_empty_after_bestanden():
    """Test gedrag wanneer er niets na 'bestanden' komt."""
    input_path = "/home/user/bestanden"
    expected = ""
    assert normalize_path(input_path) == expected

def test_normalize_path_multiple_bestanden():
    """Test gedrag met meerdere 'bestanden' in het pad."""
    input_path = "/home/bestanden/user/bestanden/file.txt"
    expected = "user/bestanden/file.txt"
    assert normalize_path(input_path) == expected

def test_normalize_path_base_dir_not_in_path():
    """Test gedrag wanneer base_dir niet in het pad voorkomt."""
    input_path = "/home/user/project/data/file.txt"
    base_dir = "/different/path"
    expected = "/home/user/project/data/file.txt"
    assert normalize_path(input_path, base_dir) == expected

def test_date_type_iso_format():
    """Test date_type met ISO formaat (yyyy-mm-dd)."""
    result = date_type("2023-12-31")
    assert isinstance(result, Literal)
    assert result.datatype == XSD.date
    assert result.value == date(2023, 12, 31)

def test_date_type_year_only():
    """Test date_type met alleen een jaartal."""
    result = date_type("2023")
    assert isinstance(result, Literal)
    assert result.datatype == XSD.gYear
    assert result.value == date(2023, 1, 1)  # gYear wordt omgezet naar 1 januari van dat jaar

def test_date_type_dutch_format():
    """Test date_type met Nederlands datumformaat (dd-mm-yyyy)."""
    result = date_type("31-12-2023")
    assert isinstance(result, Literal)
    assert result.datatype == XSD.date
    assert result.value == date(2023, 12, 31)

def test_date_type_dutch_format_single_digits():
    """Test date_type met Nederlands datumformaat met enkele cijfers (d-m-yyyy)."""
    result = date_type("1-4-2023")
    assert isinstance(result, Literal)
    assert result.datatype == XSD.date
    assert result.value == date(2023, 4, 1)

def test_date_type_invalid_format():
    """Test date_type met ongeldig datumformaat."""
    result = date_type("invalid-date")
    assert isinstance(result, Literal)
    assert result.datatype is None
    assert result.value == "invalid-date"  # Invalid blijft een string

def test_date_type_partial_date():
    """Test date_type met onvolledig datumformaat."""
    result = date_type("2023-12")
    assert isinstance(result, Literal)
    assert result.datatype is None
    assert result.value == "2023-12"  # Partial date blijft een string
