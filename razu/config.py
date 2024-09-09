class Config:
    """Singleton Configuration class for managing application settings.

    This class allows for setting dynamic configuration variables
    and protects them from being overwritten unintentionally.

    Attributes:
        _instance (Config): A single instance of the Config class.
        _settings (dict): Internal storage for configuration settings.

    Examples:
        config = Config(myvar="value1", another_var=42)
        print(config.myvar)  # Output: value1
    """

    _instance = None

    def __new__(cls, **initial_settings):
        """Creates a new Config instance or returns the existing instance.

        Args:
            **initial_settings: Arbitrary keyword arguments used to
                set the initial configuration variables.

        Returns:
            Config: The singleton instance of the Config class.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.__dict__['_settings'] = {}  
        if initial_settings:
            cls._instance._set_initial_settings(initial_settings)
        return cls._instance

    def _set_initial_settings(self, initial_settings):
        """Sets the initial configuration variables.

        Args:
            initial_settings (dict): A dictionary with initial configuration settings.
        """
        for name, value in initial_settings.items():
            self.__setattr__(name, value)

    def __setattr__(self, name, value):
        """Adds a configuration variable or raises an error if it already exists.

        Args:
            name (str): The name of the configuration variable.
            value: The value of the configuration variable.

        Raises:
            ValueError: If the configuration variable is already set.
        """
        if name in self.__dict__['_settings']:
            raise ValueError(f"The configuration variable '{name}' cannot be overwritten.")
        else:
            self.__dict__['_settings'][name] = value

    def __getattr__(self, name):
        """Retrieves the value of a configuration variable.

        Args:
            name (str): The name of the configuration variable.

        Returns:
            The value of the configuration variable if it exists.

        Raises:
            AttributeError: If the configuration variable does not exist.
        """
        if name in self.__dict__['_settings']:
            return self.__dict__['_settings'][name]
        else:
            raise AttributeError(f"The configuration variable '{name}' does not exist.")





# import os
#
# class Config:
#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(Config, cls).__new__(cls)
#         return cls._instance

#     def __init__(self):
#         if not hasattr(self, 'initialized'):
#             self.initialized = True
#             self.RAZU_base_URI = "https://data.razu.nl/"
#             self.RAZU_file_id = "NL-WbDRAZU"
#             self._creator = None     # voorbeeld: "G321" voor Gemeente Houten
#             self._archive = None     # / toegang, voorbeeld "661" , als in Mais Flexis
#             self._sparql_prefix = "https://api.data.razu.nl/datasets/id/"  # unfold to "https://api.data.razu.nl/datasets/id/{group}/sparql" 
#             self.save = False
#             self.save_dir = "test"
#         self._update_prefixes()

#     def _update_prefixes(self):
#         self.filename_prefix = f"{self.RAZU_file_id}-{self._creator}-{self._archive}" # voorbeeld "NL-WbDRAZU-G312-661"
#         self.URI_prefix = f"{self.RAZU_base_URI}{self.filename_prefix}"             # voorbeeld ""https://data.razu.nl/NL-WbDRAZU-G312-661"

#     @classmethod
#     def set_params(
#         cls, 
#         save = False, 
#         save_dir = "test", 
#         creator = None, 
#         archive = None, 
#         sparql_prefix = "https://api.data.razu.nl/datasets/id/"  # unfold to "https://api.data.razu.nl/datasets/id/{group}/sparql" 
#     ):
#         instance = cls()
#         instance.save = save
#         instance.save_dir = save_dir
#         instance._creator = creator
#         instance._archive = archive
#         instance._sparql_prefix = sparql_prefix
#         instance._update_prefixes()
        
#         if instance.save and instance.save_dir is not None:
#             os.makedirs(instance.save_dir, exist_ok=True)

#     @property
#     def creator(self):
#         return self._creator

#     @property
#     def archive(self):
#         return self._archive

#     @property
#     def sparql_prefix(self):
#         return self._sparql_prefix
