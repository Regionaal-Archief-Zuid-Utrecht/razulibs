from razu.incrementer import Incrementer

def test_default_initialization():
    """Test of de `Incrementer` begint bij 1 als geen startnummer is opgegeven."""
    incrementer = Incrementer()
    
    # De eerste keer dat we next aanroepen, moet 1 worden geretourneerd
    assert incrementer.next() == 1
    # De tweede keer moet het 2 zijn
    assert incrementer.next() == 2


def test_custom_initialization():
    """Test of de `Incrementer` begint bij het opgegeven startnummer."""
    incrementer = Incrementer(start_number=10)
    
    # De eerste keer dat we next aanroepen, moet 10 worden geretourneerd
    assert incrementer.next() == 10
    # De tweede keer moet het 11 zijn
    assert incrementer.next() == 11


def test_multiple_increments():
    """Test of de `Incrementer` correct meerdere keren incrementeert."""
    incrementer = Incrementer()
    
    # De eerste increment moet 1 zijn
    assert incrementer.next() == 1
    # De tweede increment moet 2 zijn
    assert incrementer.next() == 2
    # De derde increment moet 3 zijn
    assert incrementer.next() == 3
