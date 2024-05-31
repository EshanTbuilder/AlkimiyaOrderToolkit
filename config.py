import os

class Config:
    """ Singleton configuration class to load and store configuration settings from environment variables. """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """ Initialize method to load all configuration settings. """
        # self.feature_enabled = self.get_boolean_env_var("FEATURE_ENABLED", default_value=False)
        pass

    @staticmethod
    def get_bool(env_var_name, default_value=False):
        """ Retrieve a boolean environment variable.
        
        Args:
            env_var_name (str): The name of the environment variable.
            default_value (bool): The default value to return if the environment variable is not set.
        
        Returns:
            bool: The value of the environment variable converted to a boolean.
        """
        value = os.getenv(env_var_name)
        if value is None:
            return default_value
        value = value.lower()
        return value in ["true", "1", "t", "y", "yes"]
    @staticmethod
    def get_str(env_var_name, default_value=None):
        """ Retrieve a boolean environment variable.
        
        Args:
            env_var_name (str): The name of the environment variable.
            default_value (str): The default value to return if the environment variable is not set.
        
        Returns:
            str: The value of the environment variable.
        """
        value = os.getenv(env_var_name)
        if value is None:
            return default_value
        return value