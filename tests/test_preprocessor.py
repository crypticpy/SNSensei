import pytest
from app.preprocessor import preprocess_text, preprocess_ticket, remove_sensitive_info, normalize_unicode

def test_remove_sensitive_info():
    text = "Contact john.doe@example.com or call 123-456-7890. Server IP: 192.168.1.1"
    result = remove_sensitive_info(text)
    assert "john.doe@example.com" not in result
    assert "123-456-7890" not in result
    assert "192.168.1.1" not in result
    assert "[EMAIL]" in result
    assert "[PHONE_NUMBER]" in result
    assert "[IP_ADDRESS]" in result

def test_preprocess_text():
    text = "  <p>User can't login. Error: 'Invalid password'</p>  \n\n http://example.com "
    result = preprocess_text(text)
    assert "<p>" not in result
    assert "</p>" not in result
    assert "http://example.com" not in result
    assert "[URL]" in result
    assert result.strip() == "User can't login. Error: 'Invalid password' [URL]"

def test_preprocess_ticket():
    ticket = {
        "id": "T123",
        "description": "User can't access email. IP: 192.168.1.1",
        "category": "Email",
        "priority": 1,
        "is_resolved": False,
        "tags": ["email", "access"]
    }
    columns = ["id", "description", "category", "priority", "is_resolved", "tags"]
    tracking_index_column = "id"

    result = preprocess_ticket(ticket, columns, tracking_index_column)

    assert result["id"] == "T123"
    assert "[IP_ADDRESS]" in result["description"]
    assert "192.168.1.1" not in result["description"]
    assert result["category"] == "Email"
    assert result["priority"] == "1"
    assert result["is_resolved"] == "false"
    assert result["tags"] == "['email', 'access']"
    assert result["tracking_index"] == "T123"

def test_preprocess_ticket_missing_columns():
    ticket = {"id": "T123", "description": "Test"}
    columns = ["id", "description", "category"]
    tracking_index_column = "id"

    result = preprocess_ticket(ticket, columns, tracking_index_column)

    assert result["id"] == "T123"
    assert result["description"] == "Test"
    assert result["category"] == "[MISSING]"
    assert result["tracking_index"] == "T123"

def test_preprocess_ticket_empty_values():
    ticket = {"id": "T123", "description": "", "category": None}
    columns = ["id", "description", "category"]
    tracking_index_column = "id"

    result = preprocess_ticket(ticket, columns, tracking_index_column)

    assert result["id"] == "T123"
    assert result["description"] == "[EMPTY]"
    assert result["category"] == "[EMPTY]"
    assert result["tracking_index"] == "T123"

def test_normalize_unicode():
    text = "Café ñ àéîøü"
    result = normalize_unicode(text)
    assert result == "Cafe n aeiou"

if __name__ == '__main__':
    pytest.main()