import re
from typing import Dict, List, Optional

import pandas as pd


def remove_sensitive_info(text: str) -> str:
    """Removes sensitive information like IP addresses and phone numbers from the text."""
    text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '', text)  # IP addresses
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '', text)  # US phone numbers
    return text


def strip_email_signatures_and_links(text: str) -> str:
    """Strips email signatures, image paths, and hyperlinks from the text."""
    text = re.split(r'(--|_____)', text, maxsplit=1)[0].strip()
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # Markdown images
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Markdown links
    text = re.sub(r'<img[^>]*>', '', text)  # HTML images
    text = re.sub(r'<a[^>]*>.*?</a>', '', text)  # HTML links
    return text


def preprocess_text(text: str) -> str:
    """Applies both sensitive info removal and signature/link stripping to the text."""
    text = remove_sensitive_info(text)
    text = strip_email_signatures_and_links(text)
    return text


def preprocess_ticket(ticket: Dict, columns: List[str], tracking_index_column: Optional[str] = None) -> Dict:
    preprocessed_ticket = {}
    for column in columns:
        if column in ticket:
            value = ticket[column]
            if pd.notna(value) and value != "":
                if isinstance(value, str):
                    preprocessed_ticket[column] = preprocess_text(value)
                else:
                    preprocessed_ticket[column] = str(value)
    if tracking_index_column and tracking_index_column in ticket:
        tracking_index_value = ticket[tracking_index_column]
        if pd.notna(tracking_index_value) and tracking_index_value != "":
            preprocessed_ticket["tracking_index"] = str(tracking_index_value)
    return preprocessed_ticket
