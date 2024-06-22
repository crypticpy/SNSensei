import pytest
from unittest.mock import patch
from app.config import Config, get_config


def test_config_load_from_env_file():
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "OPENAI_API_KEY=test_key\n"
            "MODEL=gpt-4\n"
        )
        config = Config()

    assert config.get('OPENAI_API_KEY') == 'test_key'
    assert config.get('MODEL') == 'gpt-4'


def test_config_load_from_env_vars():
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'env_test_key', 'MODEL': 'env_gpt-4'}):
        config = Config()

    assert config.get('OPENAI_API_KEY') == 'env_test_key'
    assert config.get('MODEL') == 'env_gpt-4'


def test_config_default_values():
    config = Config()

    assert config.get('API_TYPE') == 'openai'
    assert config.get('MAX_TOKENS') == '300'
    assert config.get('TEMPERATURE') == '0.1'


def test_get_config():
    config = get_config()
    assert isinstance(config, Config)


def test_config_missing_required():
    with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
        config = Config()

    assert config.get('OPENAI_API_KEY') is None


if __name__ == '__main__':
    pytest.main()