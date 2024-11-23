class Config:
    """Singleton Configuration class for managing application settings.

    This class allows for setting dynamic configuration variables
    and protects them from being overwritten unintentionally.

    Attributes:
        _instance (Config): A single instance of the Config class.

    Examples:
        config = Config(myvar="value1", another_var=42)
        print(config.myvar)  # Output: value1
    """

    _instance = None

    def __new__(cls, **initial_settings) -> "Config":
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
        """Adds a configuration variable or raises an error if it already exists."""
        if name in self.__dict__['_settings']:
            raise ValueError(f"The configuration variable '{name}' with value {self.__dict__['_settings'][name]} cannot be overwritten.")
        else:
            self.__dict__['_settings'][name] = value

    def __getattr__(self, name):
        """Retrieves the value of a configuration variable."""
        if name in self.__dict__['_settings']:
            return self.__dict__['_settings'][name]
        else:
            raise AttributeError(f"The configuration variable '{name}' does not exist.")

    @classmethod
    def reset(cls):
        """Resets the configuration singleton to its initial state."""
        cls._instance = None
