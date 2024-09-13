from .config import Config

class RazuConfig(Config):
    """A subclass of Config for adding business-specific logic and default values."""

    def __new__(cls, **initial_settings) -> "RazuConfig":
       
        default_settings = {
            "RAZU_base_URI": "https://data.razu.nl/" ,
            "RAZU_file_id": "NL-WbDRAZU",
            "sparql_endpoint_prefix": "https://api.data.razu.nl/datasets/id/"
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
    def filename_prefix(self):
        """Generates a filename prefix like 'NL-WbDRAZU-G312-661-'."""
        try:
            return f"{self.RAZU_file_id}-{self.archive_creator_id}-{self.archive_id}-"
        except AttributeError:
            raise ValueError("Missing attributes")

    @property
    def URI_prefix(self):
        """Generates a URI prefix like 'https://data.razu.nl/NL-WbDRAZU-G312-661-'."""
        try:
            return f"{self.RAZU_base_URI}id/object/{self.filename_prefix}"
        except AttributeError:
            raise ValueError("Missing attributes")


