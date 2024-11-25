from .config import Config


class RazuConfig(Config):
    """A subclass of Config for adding business-specific logic and default values."""

    def __new__(cls, **initial_settings) -> "RazuConfig":

        default_settings = {
            "razu_base_uri": "https://data.razu.nl/",
            "razu_file_id": "NL-WbDRAZU",
            "sparql_endpoint_prefix": "https://api.data.razu.nl/datasets/id/",
            "sparql_endpoint_suffix": "/sparql",
            "resource_identifier_segment": "id",
            "metadata_suffix": "meta",
            "metadata_extension": "json",
        }
        instance = super(RazuConfig, cls).__new__(cls, **initial_settings)

        for key, value in default_settings.items():
            if not hasattr(instance, key):
                setattr(instance, key, value)

        return instance

    @property
    def filename_prefix(self):
        """Generates a filename prefix like 'NL-WbDRAZU-G312-661'."""
        try:
            return f"{self.razu_file_id}-{self.archive_creator_id}-{self.archive_id}"
        except AttributeError:
            raise ValueError("Missing attributes")

    @property
    def object_uri_prefix(self):
        """Generates a URI prefix like 'https://data.razu.nl/id/object/NL-WbDRAZU-G312-661'."""
        return self._uri_prefix('object')

    @property
    def event_uri_prefix(self):
        """Generates a URI prefix like 'https://data.razu.nl/id/event/NL-WbDRAZU-G312-661'."""
        return self._uri_prefix('event')

    @property
    def manifest_filename(self):
        """ Generates the filename of the manifest. """
        try:
            return f"{self.filename_prefix}.manifest.json"
        except AttributeError:
            raise ValueError("Missing attributes")
    
    @property
    def eventlog_filename(self):
        """ Generates the filename of the manifest. """
        try:
            return f"{self.filename_prefix}.eventlog.json"
        except AttributeError:
            raise ValueError("Missing attributes")

    @property
    def eventlog_filename(self):
        """ Generates the filename of the premis eventlog. """
        try:
            return f"{self.filename_prefix}.eventlog.json"
        except AttributeError:
            raise ValueError("Missing attributes")
        

    @property
    def cdn_base_uri(self):
        try:
            return f"https://{self.archive_creator_id.lower()}.opslag.razu.nl/"
        except AttributeError:
            raise ValueError("Missing attributes")


    
    def _uri_prefix(self, kind):
        """Generates a URI prefix like 'https://data.razu.nl/id/{kind}/NL-WbDRAZU-G312-661'."""
        try:
            return f"{self.razu_base_uri}{self.resource_identifier_segment}/{kind}/{self.filename_prefix}"
        except AttributeError:
            raise ValueError("Missing attributes")