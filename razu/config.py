import os

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.RAZU_base_URI = "https://data.razu.nl/"
            self.RAZU_file_id = "NL-WbDRAZU"
            self._creator = None     # voorbeeld: "G321" voor Gemeente Houten
            self._archive = None     # / toegang, voorbeeld "661" , als in Mais Flexis
            self.save = False
            self.save_dir = "test"
        self._update_prefixes()

    def _update_prefixes(self):
        self.filename_prefix = f"{self.RAZU_file_id}-{self._creator}-{self._archive}" # voorbeeld "NL-WbDRAZU-G312-661"
        self.URI_prefix = f"{self.RAZU_base_URI}{self.filename_prefix}"             # voorbeeld ""https://data.razu.nl/NL-WbDRAZU-G312-661"

    @classmethod
    def set_params(cls, save=False, save_dir="test", creator=None, archive=None):
        instance = cls()
        instance.save = save
        instance.save_dir = save_dir
        instance._creator = creator
        instance._archive = archive
        instance._update_prefixes()
        
        if instance.save and instance.save_dir is not None:
            os.makedirs(instance.save_dir, exist_ok=True)

    @property
    def creator(self):
        return self._creator

    @property
    def archive(self):
        return self._archive
