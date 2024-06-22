import json
import logging
from typing import Dict, List, Any, Union

logger = logging.getLogger(__name__)

def postprocess_output(output: Union[str, Dict[str, Any]], analysis_types: List[str],
                       preprocessed_ticket: Dict[str, Any], include_explanations: bool = True) -> Dict[str, Any]:
    if isinstance(output, str):
        try:
            output = output.strip()
            # Remove any potential markdown code block indicators
            output = output.replace('```json', '').replace('```', '')
            analyzed_data = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {str(e)}")
            logger.error(f"Raw output: {output}")
            analyzed_data = {}
    else:
        analyzed_data = output

    # Start with all the preprocessed ticket data
    result = preprocessed_ticket.copy()

    # Process each selected analysis type
    for analysis_type in analysis_types:
        # The main result key is the same as the analysis type
        result_key = analysis_type
        # The explanation key adds "_explanation" to the analysis type
        explanation_key = f"{analysis_type}_explanation"

        # Handle potential variations in key names
        normalized_key = result_key.lower().replace(' ', '_')
        normalized_explanation_key = explanation_key.lower().replace(' ', '_')

        # Look for the analysis result using both original and normalized keys
        result[result_key] = analyzed_data.get(result_key,
                                               analyzed_data.get(normalized_key,
                                                                 "N/A"))

        if include_explanations:
            result[explanation_key] = analyzed_data.get(explanation_key,
                                                        analyzed_data.get(normalized_explanation_key,
                                                                          ""))

        # If the value is a dictionary or list, convert it to a string
        if isinstance(result[result_key], (dict, list)):
            result[result_key] = json.dumps(result[result_key])
        if include_explanations and isinstance(result[explanation_key], (dict, list)):
            result[explanation_key] = json.dumps(result[explanation_key])

    return result

def validate_postprocessed_output(result: Dict[str, Any], analysis_types: List[str], include_explanations: bool) -> List[str]:
    """
    Validate the postprocessed output to ensure all required fields are present.

    Args:
        result (Dict[str, Any]): The postprocessed output.
        analysis_types (List[str]): List of analysis types that were requested.
        include_explanations (bool): Whether explanations were requested.

    Returns:
        List[str]: A list of missing fields, if any.
    """
    missing_fields = []
    required_fields = ["tracking_index"]

    for analysis_type in analysis_types:
        if analysis_type not in result:
            missing_fields.append(analysis_type)
        if include_explanations and f"{analysis_type}_explanation" not in result:
            missing_fields.append(f"{analysis_type}_explanation")

    return missing_fields

def debug_output(result: Dict[str, Any]) -> None:
    """
    Print debug information for a processed ticket.

    Args:
        result (Dict[str, Any]): The processed ticket data.
    """
    print(f"Processed ticket: {result.get('tracking_index', 'Unknown')}")
    for key, value in result.items():
        if key != 'tracking_index':
            print(f"{key}: {value}")
    print("---")

# Example usage
if __name__ == "__main__":
    sample_output = {
        "extract_product": "Email Client",
        "extract_product_explanation": "The ticket mentions issues with accessing email.",
        "summarize_ticket": "Email access problem",
        "summarize_ticket_explanation": "User is unable to log into their email account.",
        "ticket_quality": "Good",
        "ticket_quality_explanation": "The ticket provides clear information about the issue."
    }

    sample_preprocessed_ticket = {
        "description": "User cannot access their email account. Getting 'invalid credentials' error.",
        "tracking_index": "TIC-001"
    }

    sample_analysis_types = ["extract_product", "summarize_ticket", "ticket_quality"]

    # Test with explanations
    result_with_explanations = postprocess_output(sample_output, sample_analysis_types, sample_preprocessed_ticket, include_explanations=True)
    print("Result with explanations:")
    print(json.dumps(result_with_explanations, indent=2))

    missing_fields = validate_postprocessed_output(result_with_explanations, sample_analysis_types, include_explanations=True)
    if missing_fields:
        print(f"Missing fields (with explanations): {', '.join(missing_fields)}")
    else:
        print("All required fields are present (with explanations).")

    debug_output(result_with_explanations)

    print("\n" + "="*50 + "\n")

    # Test without explanations
    result_without_explanations = postprocess_output(sample_output, sample_analysis_types, sample_preprocessed_ticket, include_explanations=False)
    print("Result without explanations:")
    print(json.dumps(result_without_explanations, indent=2))

    missing_fields = validate_postprocessed_output(result_without_explanations, sample_analysis_types, include_explanations=False)
    if missing_fields:
        print(f"Missing fields (without explanations): {', '.join(missing_fields)}")
    else:
        print("All required fields are present (without explanations).")

    debug_output(result_without_explanations)