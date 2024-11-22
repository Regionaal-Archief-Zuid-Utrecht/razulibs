import pytest
from razu.util import normalize_path

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
