from .config import Config


class RazuConfig(Config):
    """A subclass of Config for adding business-specific logic and default values."""

    def __new__(cls, **initial_settings) -> "RazuConfig":

        default_settings = {
            "RAZU_base_URI": "https://data.razu.nl/",
            "RAZU_file_id": "NL-WbDRAZU",
            "sparql_endpoint_prefix": "https://api.data.razu.nl/datasets/id/",
            "sparql_endpoint_suffix": "/sparql",
            "resource_identifier": "id"
        }
        instance = super(RazuConfig, cls).__new__(cls, **initial_settings)

        for key, value in default_settings.items():
            if not hasattr(instance, key):
                setattr(instance, key, value)

        return instance

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
