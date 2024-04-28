from typing import Optional


def generate_prompt(ticket: dict, columns: list, analysis_types: list,
                    tracking_index_column: Optional[str] = None) -> str:
    """Generates the prompt for the LLM based on the ticket, selected columns, and analysis types."""
    ticket_info = "\n".join([f"{column}: {ticket[column]}" for column in columns if column in ticket])

    if not ticket_info:
        ticket_info = "No information available for the selected columns."

    main_prompt = f"IMPORTANT: Please provide your response in a complete and well-formatted JSON format as specified below.\n\nAnalyze the following trouble ticket information:\n\n{ticket_info}\n\n"

    analysis_instructions = []

    analysis_instructions = []

    if "extract_product" in analysis_types:
        analysis_instructions.append(
            "Extract the product or system mentioned in the ticket. "
            "The product could be a software (e.g., MS Word, Outlook), hardware brand or type (e.g., Toshiba Laptop, Printer), "
            "or a general category (e.g., Word Processor, Email). "
            "If no specific product is mentioned, try to provide a general category or type. "
            "If no product or category can be determined, respond with 'N/A'."
        )

    if "summarize_ticket" in analysis_types:
        analysis_instructions.append(
            "Provide a concise 2 to 5 word summary of the ticket. "
            "The summary should capture the main issue or request described in the ticket."
        )

    if "resolution_appropriateness" in analysis_types:
        analysis_instructions.append(
            "Determine if the resolution provided was appropriate or not, based on the ticket description and resolution details. "
            "Consider factors such as whether the resolution addresses the main issue, provides a clear solution, "
            "and follows standard procedures or best practices."
        )

    if "ticket_quality" in analysis_types:
        analysis_instructions.append(
            "Determine the quality and completeness of the ticket description and incident details. "
            "Classify the ticket quality as 'good', 'fair', or 'poor' based on the level of detail, clarity, and relevance of the information provided. "
            "A 'good' ticket should have a clear and detailed description of the issue, steps to reproduce (if applicable), "
            "and any relevant context or background information. "
            "A 'fair' ticket may have some missing or unclear details but still provides enough information to understand the issue. "
            "A 'poor' ticket lacks essential details, is unclear, or contains irrelevant information."
        )

    if "sentiment_analysis" in analysis_types:
        analysis_instructions.append(
            "Determine the sentiment expressed by the customer or user in the ticket. "
            "Classify the sentiment as 'positive', 'negative', 'neutral', or 'N/A' if no clear sentiment can be determined. "
            "Consider the tone, language, and overall expression in the ticket description and any additional comments. "
            "A 'positive' sentiment may include expressions of gratitude, satisfaction, or positive feedback. "
            "A 'negative' sentiment may include expressions of frustration, dissatisfaction, or criticism. "
            "A 'neutral' sentiment is present when the tone is factual, impartial, or lacks strong emotional indicators."
        )

    main_prompt += "Please perform the following analysis:\n" + "\n".join(
        f"{i + 1}. {instruction}" for i, instruction in enumerate(analysis_instructions))

    main_prompt += "\n\nIf the information provided in the ticket is insufficient to perform any of the requested analyses, respond with 'N/A' for that specific analysis."

    main_prompt += "\n\nExample of a well-formatted JSON response:\n"
    main_prompt += """{
          "product": "Email",
          "product_explanation": "The ticket mentions issues with accessing email, indicating the product is related to the email system.",
          "summary": "Unable to access email",
          "summary_explanation": "The main issue is that the user cannot access their email account.",
          "resolution_appropriate": true,
          "resolution_explanation": "The resolution steps provided, such as checking network connection and verifying login credentials, are appropriate troubleshooting steps for email access issues.",
          "ticket_quality": "good",
          "quality_explanation": "The ticket provides clear details about the issue and the steps already taken by the user.",
          "sentiment": "neutral",
          "sentiment_explanation": "The user's tone is neutral and factual, focusing on describing the issue without expressing strong emotions."
        }"""

    main_prompt += "\n\nIf you encounter any issues generating a complete JSON response for a specific analysis type, please provide a default response for that analysis type and include an error message indicating the issue."

    main_prompt += "\n\nMake sure to provide a brief but informative explanation for your response to each analysis type, enclosed in double quotes."

    # Start JSON output format.
    main_prompt += "\n\nProvide your response in the following JSON format:\n{"
    json_elements = []
    if tracking_index_column:
        json_elements.append(f'  "tracking_index": "{ticket.get(tracking_index_column, "")}"')

    # Generate JSON output properties for each analysis type.
    analysis_properties = []
    if "extract_product" in analysis_types:
        analysis_properties.append('  "product": "<extracted_product>",\n  "product_explanation": "<explanation>"')
    if "summarize_ticket" in analysis_types:
        analysis_properties.append('  "summary": "<ticket_summary>",\n  "summary_explanation": "<explanation>"')
    if "resolution_appropriateness" in analysis_types:
        analysis_properties.append(
            '  "resolution_appropriate": <true|false|"N/A">,\n  "resolution_explanation": "<explanation>"')
    if "ticket_quality" in analysis_types:
        analysis_properties.append('  "ticket_quality": "<good|fair|poor>",\n  "quality_explanation": "<explanation>"')
    if "sentiment_analysis" in analysis_types:
        analysis_properties.append(
            '  "sentiment": "<positive|negative|neutral|N/A>",\n  "sentiment_explanation": "<explanation>"')

    # Concatenate JSON properties, handling commas correctly.
    if analysis_properties:
        json_elements.extend(analysis_properties)

    main_prompt += ",\n".join(json_elements)
    main_prompt += "\n}"

    return main_prompt
