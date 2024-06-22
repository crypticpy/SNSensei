import re
from typing import Dict, List, Any, Optional
import pandas as pd
from html import unescape
import unicodedata

def remove_sensitive_info(text: str) -> str:
    """Removes sensitive information like IP addresses, email addresses, and phone numbers from the text."""
    # Remove IP addresses
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]', text)
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # Remove US phone numbers
    text = re.sub(r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b', '[PHONE_NUMBER]', text)
    return text

def strip_html_tags(text: str) -> str:
    """Removes HTML tags from the text."""
    return re.sub(r'<[^>]+>', '', text)

def normalize_whitespace(text: str) -> str:
    """Normalizes whitespace in the text."""
    return ' '.join(text.split())

def remove_urls(text: str) -> str:
    """Removes URLs from the text."""
    return re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[URL]', text)

def remove_special_characters(text: str) -> str:
    """Removes special characters from the text, keeping only letters, numbers, and basic punctuation."""
    return re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)

def normalize_unicode(text: str) -> str:
    """Normalizes Unicode characters to their closest ASCII representation."""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')

def preprocess_text(text: str) -> str:
    """Applies all text preprocessing steps."""
    text = unescape(text)  # Convert HTML entities to their corresponding characters
    text = strip_html_tags(text)
    text = remove_sensitive_info(text)
    text = remove_urls(text)
    text = normalize_unicode(text)
    text = remove_special_characters(text)
    text = normalize_whitespace(text)
    return text.strip()

def preprocess_ticket(ticket: Dict[str, Any], columns: List[str], tracking_index_column: Optional[str] = None) -> Dict[str, Any]:
    """
    Preprocesses a single ticket.

    Args:
        ticket (Dict[str, Any]): The raw ticket data.
        columns (List[str]): List of columns to include in the preprocessed ticket.
        tracking_index_column (Optional[str]): The name of the column to use as the tracking index.

    Returns:
        Dict[str, Any]: The preprocessed ticket data.
    """
    preprocessed_ticket = {}
    for column in columns:
        if column in ticket:
            value = ticket[column]
            if pd.notna(value) and value != "":
                if isinstance(value, str):
                    preprocessed_ticket[column] = preprocess_text(value)
                elif isinstance(value, (int, float)):
                    preprocessed_ticket[column] = str(value)
                elif isinstance(value, bool):
                    preprocessed_ticket[column] = str(value).lower()
                elif isinstance(value, (list, dict)):
                    preprocessed_ticket[column] = str(value)
                else:
                    preprocessed_ticket[column] = "[UNSUPPORTED_DATA_TYPE]"
            else:
                preprocessed_ticket[column] = "[EMPTY]"
        else:
            preprocessed_ticket[column] = "[MISSING]"

    if tracking_index_column and tracking_index_column in ticket:
        tracking_index_value = ticket[tracking_index_column]
        if pd.notna(tracking_index_value) and tracking_index_value != "":
            preprocessed_ticket["tracking_index"] = str(tracking_index_value)
        else:
            preprocessed_ticket["tracking_index"] = "[EMPTY_TRACKING_INDEX]"
    elif tracking_index_column:
        preprocessed_ticket["tracking_index"] = "[MISSING_TRACKING_INDEX]"

    return preprocessed_ticket

# Example usage
if __name__ == "__main__":
    sample_ticket = {
        "id": 12345,
        "description": "User can't access email. Error message: 'Invalid credentials'. IP: 192.168.1.1",
        "category": "Email",
        "priority": "High",
        "customer_email": "john.doe@example.com",
        "customer_phone": "+1 (555) 123-4567",
        "notes": "<p>Customer tried resetting password but still can't log in.</p>",
        "url": "https://support.example.com/ticket/12345",
        "is_resolved": False,
        "resolution_time": 3.5,
        "tags": ["email", "login", "credentials"],
    }

    columns = ["id", "description", "category", "priority", "notes", "is_resolved", "resolution_time", "tags"]
    tracking_index_column = "id"

    preprocessed = preprocess_ticket(sample_ticket, columns, tracking_index_column)
    for key, value in preprocessed.items():
        print(f"{key}: {value}")