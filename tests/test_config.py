import pytest
from razu.config import Config  

def test_singleton_behavior():
    """Test dat de Config class zich gedraagt als een singleton."""
    config1 = Config(myvar="value1")
    config2 = Config(another_var="value2")
    
    # Controleer dat beide variabelen op hetzelfde object wijzen
    assert config1 is config2

def test_initial_settings():
    """Test het instellen van configuratievariabelen bij initialisatie."""
    config = Config(myvar2="value1", another_var2=42)
    
    # Controleer dat de variabelen correct zijn ingesteld
    assert config.myvar2 == "value1"
    assert config.another_var2 == 42

def test_variable_cannot_be_overwritten():
    """Test dat een configuratievariabele niet kan worden overschreven."""
    config = Config(existing_var="initial_value")
    
    # Poging om dezelfde variabele opnieuw in te stellen moet een fout veroorzaken
    with pytest.raises(ValueError):
        config.existing_var = "new_value"

def test_get_non_existent_variable():
    """Test dat het ophalen van een niet-bestaande configuratievariabele een AttributeError veroorzaakt."""
    config = Config()
    
    # Poging om een niet-bestaande variabele op te halen moet een fout veroorzaken
    with pytest.raises(AttributeError):
        _ = config.non_existent_var

def test_persistent_state_across_instances():
    """Test dat de configuratievariabelen persistent blijven bij meerdere instanties."""
    config1 = Config(myvar3="value1")
    config2 = Config()

    # Controleer dat de tweede instantie toegang heeft tot de variabele ingesteld door de eerste instantie
    assert config2.myvar3 == "value1"

    # Controleer dat nieuwe variabelen kunnen worden toegevoegd door de tweede instantie
    config2.another_var4 = "value2"
    assert config1.another_var4 == "value2"
