import os
from typing import Any
from dotenv import load_dotenv


class Config:
    def __init__(self):
        self.config = {}
        self._load_config()

    def _load_config(self):
        # Load from .env file
        load_dotenv()

        # Load all environment variables
        for key, value in os.environ.items():
            self.config[key.upper()] = value

        # Set default values for missing configurations
        self._set_defaults()

    def _set_defaults(self):
        defaults = {
            'API_TYPE': 'openai',
            'MODEL': 'gpt-4',
            'MAX_TOKENS': '300',
            'TEMPERATURE': '0.1',
            'INITIAL_BATCH_SIZE': '10',
            'MAX_BATCH_SIZE': '100',
            'BATCH_SIZE_FACTOR': '2.0',
            'MAX_WORKERS': '50',
            'OUTPUT_FILE_PREFIX': 'processed_tickets',
            'INCLUDE_RAW_RESPONSE': 'True',
            'LOG_LEVEL': 'INFO',
            'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(message)s',
            'MAX_RETRIES': '5',
            'INITIAL_RETRY_DELAY': '1.0',
            'RETRY_BACKOFF_FACTOR': '2.0',
            # OpenAI specific defaults
            'OPENAI_API_KEY': '',
            # Azure OpenAI specific defaults
            'AZURE_OPENAI_API_VERSION': '2023-05-15',
            'AZURE_OPENAI_API_BASE': '',
            'AZURE_OPENAI_API_KEY': '',
            'AZURE_OPENAI_DEPLOYMENT_NAME': '',
        }
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key.upper(), default)

    def set(self, key: str, value: Any):
        self.config[key.upper()] = value

    @property
    def is_azure_openai(self):
        return self.get('API_TYPE', '').lower() == 'azure'

    def __getattr__(self, name: str) -> Any:
        return self.get(name.upper())

    def to_dict(self):
        return self.config.copy()


def get_config() -> Config:
    return Config()


# Example usage and debugging
if __name__ == "__main__":
    config = get_config()
    print("Current configuration:")
    for key, value in config.to_dict().items():
        if 'KEY' in key:
            print(f"{key}: {'<redacted>' if value else 'Not Set'}")
        else:
            print(f"{key}: {value}")

    # Test accessing config values
    print("\nAccessing config values:")
    print(f"API Type: {config.api_type}")
    print(f"Model: {config.model}")
    print(f"Is Azure OpenAI: {config.is_azure_openai}")

    # Test setting a value
    config.set('TEST_KEY', 'test_value')
    print(f"Test Key: {config.get('TEST_KEY')}")

    # Validate required configurations
    required_configs = ['OPENAI_API_KEY', 'MODEL', 'MAX_TOKENS'] if not config.is_azure_openai else [
        'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_API_BASE', 'AZURE_OPENAI_DEPLOYMENT_NAME']
    missing_configs = [conf for conf in required_configs if not config.get(conf)]
    if missing_configs:
        print(f"\nWARNING: The following required configurations are missing: {', '.join(missing_configs)}")
    else:
        print("\nAll required configurations are set.")