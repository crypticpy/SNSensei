import pytest
import logging
from app.logging_config import setup_logging


def test_setup_logging():
    logger = setup_logging()

    assert isinstance(logger, logging.Logger)
    assert logger.name == "ticket_analyzer"
    assert logger.level == logging.INFO

    # Check handlers
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert isinstance(logger.handlers[1], logging.FileHandler)

    # Check formatter
    for handler in logger.handlers:
        assert handler.formatter._fmt == '%(asctime)s - %(levelname)s - %(message)s'


def test_setup_logging_custom_level():
    with pytest.MonkeyPatch.context() as m:
        m.setenv('LOG_LEVEL', 'DEBUG')
        logger = setup_logging()

    assert logger.level == logging.DEBUG


if __name__ == '__main__':
    pytest.main()