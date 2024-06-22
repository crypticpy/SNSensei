import pytest
from app.postprocessor import postprocess_output, validate_postprocessed_output

def test_postprocess_output():
    output = {
        "extract_product": "Email Client",
        "extract_product_explanation": "The ticket mentions email access issues.",
        "summarize_ticket": "Email access problem",
        "summarize_ticket_explanation": "User unable to log into email account.",
        "ticket_quality": "Good",
        "ticket_quality_explanation": "The ticket provides clear information about the issue."
    }
    preprocessed_ticket = {
        "description": "User cannot access their email account. Getting 'invalid credentials' error.",
        "tracking_index": "TIC-001"
    }
    analysis_types = ["extract_product", "summarize_ticket", "ticket_quality"]

    result = postprocess_output(output, analysis_types, preprocessed_ticket, include_explanations=True)

    assert result["description"] == preprocessed_ticket["description"]
    assert result["tracking_index"] == preprocessed_ticket["tracking_index"]
    assert result["extract_product"] == "Email Client"
    assert result["extract_product_explanation"] == "The ticket mentions email access issues."
    assert result["summarize_ticket"] == "Email access problem"
    assert result["summarize_ticket_explanation"] == "User unable to log into email account."
    assert result["ticket_quality"] == "Good"
    assert result["ticket_quality_explanation"] == "The ticket provides clear information about the issue."

def test_postprocess_output_missing_analysis():
    output = {
        "extract_product": "Email Client",
        "extract_product_explanation": "The ticket mentions email access issues."
    }
    preprocessed_ticket = {
        "description": "User cannot access their email account.",
        "tracking_index": "TIC-001"
    }
    analysis_types = ["extract_product", "summarize_ticket"]

    result = postprocess_output(output, analysis_types, preprocessed_ticket, include_explanations=True)

    assert result["extract_product"] == "Email Client"
    assert result["summarize_ticket"] == "N/A"

def test_validate_postprocessed_output():
    result = {
        "description": "Test description",
        "tracking_index": "TIC-001",
        "extract_product": "Test Product",
        "extract_product_explanation": "Test explanation",
        "summarize_ticket": "Test summary",
        "summarize_ticket_explanation": "Test explanation"
    }
    analysis_types = ["extract_product", "summarize_ticket"]

    missing_fields = validate_postprocessed_output(result, analysis_types, include_explanations=True)
    assert len(missing_fields) == 0

def test_validate_postprocessed_output_missing_fields():
    result = {
        "description": "Test description",
        "tracking_index": "TIC-001",
        "extract_product": "Test Product"
    }
    analysis_types = ["extract_product", "summarize_ticket"]

    missing_fields = validate_postprocessed_output(result, analysis_types, include_explanations=True)
    assert "summarize_ticket" in missing_fields
    assert "extract_product_explanation" in missing_fields
    assert "summarize_ticket_explanation" in missing_fields

if __name__ == '__main__':
    pytest.main()