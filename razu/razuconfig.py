from .config import Config

class RazuConfig(Config):
    """A subclass of Config that adds business-specific logic and default values."""

    def __new__(cls, **initial_settings):
       
        default_settings = {
            "RAZU_base_URI": "https://data.razu.nl/" ,
            "RAZU_file_id": "NL-WbDRAZU",
            "sparql_prefix": "https://api.data.razu.nl/datasets/id/"
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
        """Generates a filename prefix like 'NL-WbDRAZU-G312-661'."""
        RAZU_file_id = getattr(self, 'RAZU_file_id', None)
        archive_creator_id = getattr(self, 'archive_creator_id', None)
        archive_id = getattr(self, 'archive_id', None)

        if RAZU_file_id and archive_creator_id and archive_id:
            return f"{RAZU_file_id}-{archive_creator_id}-{archive_id}-"
        else:
            raise ValueError("Missing attributes")
        
    @property
    def URI_prefix(self):
        """Generates a URI prefix like 'https://data.razu.nl/NL-WbDRAZU-G312-661'."""
        RAZU_base_URI = getattr(self, 'RAZU_base_URI', None)
        filename_prefix = self.filename_prefix

        if RAZU_base_URI and filename_prefix:
            return f"{RAZU_base_URI}{filename_prefix}" 
        else:
            raise ValueError("Missing attributes")

