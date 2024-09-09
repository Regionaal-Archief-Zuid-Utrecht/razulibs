from .config import Config

class RazuConfig(Config):
    """A subclass of Config that adds business-specific logic and default values."""

    def __new__(cls, **initial_settings):
       
        default_settings = {
            'RAZU_base_URI': "https://data.razu.nl/"
        }
        
        # If instance existst, remove any default setting that already exists to prevent overwriting
        if cls._instance is not None:
            for key in list(default_settings):
                if key in cls._instance.__dict__['_settings']:
                    del default_settings[key]


        # Combine default settings with supplied initial settings:
        default_settings.update(initial_settings)
        
        # Call parent __new__ to process settings:
        return super(RazuConfig, cls).__new__(cls, **default_settings)

    @property
    def filename(self):
        """Generates a filename based on the client name and company name."""
        client_name = getattr(self, 'client_name', None)
        company_name = getattr(self, 'company_name', None)

        if client_name and company_name:
            return f"{client_name}-{company_name}.txt"
        else:
            raise ValueError("Both 'client_name' and 'company_name' must be set to generate the filename.")
