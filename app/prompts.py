from typing import Dict, List

def generate_prompt(ticket: Dict[str, str], columns: List[str], analysis_types: List[str], include_explanations: bool) -> str:
    """
    Generates the prompt for the LLM based on the ticket, selected columns, and analysis types.

    Args:
        ticket (Dict[str, str]): The preprocessed ticket information.
        columns (List[str]): The selected columns for analysis.
        analysis_types (List[str]): The types of analysis to perform.
        include_explanations (bool): Whether to include explanations in the analysis.

    Returns:
        str: The generated prompt for the LLM.
    """
    ticket_info = "\n".join([f"{column}: {ticket.get(column, 'N/A')}" for column in columns])

    main_prompt = (
        "IMPORTANT: Analyze the following help desk ticket information and provide your response "
        "in a complete and well-formatted JSON format as specified below. Ensure all requested "
        "analysis types are included in your response.\n\n"
        f"Ticket Information:\n{ticket_info}\n\n"
        "Perform the following analyses:\n"
    )

    analysis_instructions = {
        "extract_product": (
            "Extract the product or system mentioned in the ticket. "
            "This could be software (e.g., MS Word, Outlook), hardware (e.g., Toshiba Laptop, Printer), "
            "or a general category (e.g., Word Processor, Email). "
            "If no specific product is mentioned, provide a general category. "
            "If no product or category can be determined, respond with 'N/A'."
        ),
        "summarize_ticket": (
            "Provide a concise 1 to 5 word summary of the main issue or request described in the ticket."
        ),
        "resolution_appropriateness": (
            "Determine if the resolution provided (if any) was appropriate based on the ticket description. "
            "Consider if it addresses the main issue, provides a clear solution, and follows best practices. "
            "Respond with 'appropriate', 'inappropriate', or 'N/A' if no resolution is provided."
        ),
        "ticket_quality": (
            "Evaluate the quality and completeness of the ticket description. "
            "Classify as 'good' (clear, detailed), 'fair' (some missing details), or 'poor' (unclear, lacks essential information)."
        ),
        "sentiment_analysis": (
            "Determine the sentiment expressed by the customer or user in the ticket. "
            "Classify as 'positive', 'negative', 'neutral', or 'N/A' if no clear sentiment can be determined."
        ),
        "user_proficiency_level": (
            "Assess the user's technical proficiency based on the language and complexity of the problem described. "
            "Classify as 'beginner', 'intermediate', or 'advanced'."
        ),
        "urgency_perception": (
            "Determine the perceived urgency of the issue based on the language and tone used. "
            "Classify as 'low', 'medium', 'high', or 'critical'."
        ),
        "potential_impact": (
            "Estimate the potential impact of the issue on business operations or user productivity. "
            "Classify as 'minor', 'moderate', 'major', or 'critical'."
        ),
        "information_completeness": (
            "Evaluate the completeness of the information provided for troubleshooting and resolution. "
            "Classify as 'complete', 'partial', or 'incomplete'."
        ),
        "suggested_kb_article": (
            "Recommend a relevant knowledge base article that might help resolve the issue. "
            "Provide an article ID or title if applicable, or 'N/A' if no suitable article is identified."
        ),
        "resolution_complexity": (
            "Estimate the complexity of the resolution required based on the ticket description. "
            "Classify as 'simple', 'moderate', or 'complex'."
        ),
        "historical_similarity": (
            "Identify how similar this ticket is to previously resolved tickets. "
            "Provide a percentage similarity or a brief explanation of similar past issues."
        ),
        "emotion_detection": (
            "Detect the primary emotion of the user from the language used in the ticket. "
            "Classify as 'frustrated', 'angry', 'satisfied', 'confused', or 'neutral'."
        ),
        "expected_resolution_time": (
            "Predict the expected time to resolve the issue based on its complexity. "
            "Provide an estimate (e.g., '30 minutes', '2 hours', '1 day')."
        ),
        "next_best_action": (
            "Recommend the next best action to take for resolving the issue. "
            "Provide a specific, actionable recommendation."
        ),
        "potential_root_cause": (
            "Suggest a potential root cause for the issue based on the ticket description. "
            "Provide a brief explanation of the likely underlying cause."
        ),
        "resolution_confidence": (
            "Estimate the confidence level for resolving this issue based on the information provided. "
            "Classify as 'high', 'medium', or 'low'."
        ),
        "customer_satisfaction_prediction": (
            "Predict the likely customer satisfaction if the issue is resolved as suggested. "
            "Provide a rating prediction on a scale of 1 to 5 stars."
        )
    }

    for i, analysis_type in enumerate(analysis_types, 1):
        if analysis_type in analysis_instructions:
            main_prompt += f"{i}. {analysis_instructions[analysis_type]}\n"
        else:
            main_prompt += f"{i}. Perform {analysis_type} analysis. Provide relevant insights based on the ticket information.\n"

    main_prompt += ("\nIf the information provided in the ticket is insufficient to perform any of the "
                    "requested analyses, respond with 'N/A' for that specific analysis.\n")

    main_prompt += "\nProvide your response in the following JSON format:\n{"

    json_format = []
    for analysis_type in analysis_types:
        json_format.append(f'  "{analysis_type}": "<your_analysis>",')
        if include_explanations:
            json_format.append(f'  "{analysis_type}_explanation": "<brief_explanation>",')

    main_prompt += "\n".join(json_format)[:-1]  # Remove the last comma
    main_prompt += "\n}"

    return main_prompt

# Example usage
if __name__ == "__main__":
    sample_ticket = {
        "id": "TIC-001",
        "description": "User unable to access email. Getting 'invalid credentials' error.",
        "category": "Email",
        "priority": "High"
    }
    sample_columns = ["id", "description", "category", "priority"]
    sample_analysis_types = ["extract_product", "summarize_ticket", "urgency_perception", "next_best_action"]

    prompt_with_explanations = generate_prompt(sample_ticket, sample_columns, sample_analysis_types, include_explanations=True)
    print("Prompt with explanations:")
    print(prompt_with_explanations)

    print("\n" + "="*50 + "\n")

    prompt_without_explanations = generate_prompt(sample_ticket, sample_columns, sample_analysis_types, include_explanations=False)
    print("Prompt without explanations:")
    print(prompt_without_explanations)