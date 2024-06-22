import pytest
import asyncio
from unittest.mock import Mock, patch
from app.analyzer import AsyncTicketAnalyzer
from app.config import Config


@pytest.fixture
def mock_config():
    config = Config()
    config.set('API_TYPE', 'openai')
    config.set('OPENAI_API_KEY', 'test_key')
    config.set('MODEL', 'gpt-3.5-turbo')
    config.set('MAX_TOKENS', '100')
    config.set('TEMPERATURE', '0.5')
    config.set('INITIAL_BATCH_SIZE', '5')
    config.set('MAX_BATCH_SIZE', '20')
    config.set('BATCH_SIZE_FACTOR', '2.0')
    return config


@pytest.fixture
def analyzer(mock_config):
    return AsyncTicketAnalyzer(mock_config)


@pytest.mark.asyncio
async def test_call_openai_api(analyzer):
    mock_response = {"choices": [{"message": {"content": '{"test": "response"}'}}]}

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value.__aenter__.return_value.raise_for_status = Mock()

        result = await analyzer._call_openai_api([{"role": "user", "content": "Test prompt"}])

    assert result == '{"test": "response"}'


def test_validate_llm_response(analyzer):
    valid_response = {
        "extract_product": "Test Product",
        "extract_product_explanation": "Explanation",
        "summarize_ticket": "Summary",
        "summarize_ticket_explanation": "Summary explanation"
    }
    analysis_types = ["extract_product", "summarize_ticket"]

    assert analyzer.validate_llm_response(valid_response, analysis_types, True)
    assert not analyzer.validate_llm_response(valid_response, analysis_types + ["missing_type"], True)


def test_parse_json_response(analyzer):
    valid_json = '{"key": "value"}'
    assert analyzer.parse_json_response(valid_json) == {"key": "value"}

    invalid_json = 'Not a JSON string'
    with pytest.raises(ValueError):
        analyzer.parse_json_response(invalid_json)

    partial_json = 'Some text {"key": "value"} more text'
    assert analyzer.parse_json_response(partial_json) == {"key": "value"}


@pytest.mark.asyncio
async def test_analyze_ticket(analyzer):
    mock_ticket = {
        "id": "T1",
        "description": "Test ticket",
        "category": "Test"
    }
    columns = ["id", "description", "category"]
    analysis_types = ["extract_product", "summarize_ticket"]

    mock_api_response = {
        "extract_product": "Test Product",
        "extract_product_explanation": "Explanation",
        "summarize_ticket": "Test summary",
        "summarize_ticket_explanation": "Summary explanation"
    }

    with patch.object(analyzer, '_call_openai_api', return_value=str(mock_api_response)):
        result = await analyzer.analyze_ticket(mock_ticket, columns, "id", analysis_types, True)

    assert result["extract_product"] == "Test Product"
    assert result["summarize_ticket"] == "Test summary"
    assert "extract_product_explanation" in result
    assert "summarize_ticket_explanation" in result


@pytest.mark.asyncio
async def test_analyze_tickets(analyzer):
    mock_tickets = [
        {"id": "T1", "description": "Test ticket 1"},
        {"id": "T2", "description": "Test ticket 2"}
    ]
    columns = ["id", "description"]
    analysis_types = ["extract_product"]

    mock_api_response = {
        "extract_product": "Test Product",
        "extract_product_explanation": "Explanation"
    }

    with patch.object(analyzer, '_call_openai_api', return_value=str(mock_api_response)):
        results = [batch async for batch in analyzer.analyze_tickets(mock_tickets, columns, "id", analysis_types, True)]

    assert len(results) == 1  # All tickets processed in one batch
    assert len(results[0]["batch_results"]) == 2
    assert results[0]["batch_size"] == 5  # Initial batch size
    assert results[0]["batch_error_count"] == 0


@pytest.mark.asyncio
async def test_analyze_tickets_with_error(analyzer):
    mock_tickets = [
        {"id": "T1", "description": "Test ticket 1"},
        {"id": "T2", "description": "Test ticket 2"}
    ]
    columns = ["id", "description"]
    analysis_types = ["extract_product"]

    def mock_api_call(messages):
        if messages[1]["content"].endswith("Test ticket 1"):
            return str({"extract_product": "Test Product", "extract_product_explanation": "Explanation"})
        else:
            raise ValueError("Simulated API error")

    with patch.object(analyzer, '_call_openai_api', side_effect=mock_api_call):
        results = [batch async for batch in analyzer.analyze_tickets(mock_tickets, columns, "id", analysis_types, True)]

    assert len(results) == 1
    assert len(results[0]["batch_results"]) == 2
    assert results[0]["batch_error_count"] == 1
    assert "error" in results[0]["batch_results"][1]


@pytest.mark.asyncio
async def test_azure_openai_api_call(mock_config):
    mock_config.set('API_TYPE', 'azure')
    mock_config.set('AZURE_OPENAI_API_KEY', 'azure_test_key')
    mock_config.set('AZURE_OPENAI_API_BASE', 'https://test.openai.azure.com/')
    mock_config.set('AZURE_OPENAI_API_VERSION', '2023-05-15')
    mock_config.set('AZURE_OPENAI_DEPLOYMENT_NAME', 'test-deployment')

    azure_analyzer = AsyncTicketAnalyzer(mock_config)

    mock_response = {"choices": [{"message": {"content": '{"test": "response"}'}}]}

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
        mock_post.return_value.__aenter__.return_value.raise_for_status = Mock()

        result = await azure_analyzer._call_openai_api([{"role": "user", "content": "Test prompt"}])

    assert result == '{"test": "response"}'
    # Verify that the Azure OpenAI API URL was used
    called_url = mock_post.call_args[0][0]
    assert 'https://test.openai.azure.com/' in called_url
    assert 'deployments/test-deployment' in called_url


if __name__ == '__main__':
    pytest.main()