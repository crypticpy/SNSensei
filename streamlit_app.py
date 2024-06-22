import os
import pandas as pd
import streamlit as st
import asyncio
import aiohttp
import ssl
import certifi

from typing import List

from app.analyzer import AsyncTicketAnalyzer
from app.config import get_config, Config
from app.logging_config import setup_logging
from app.utils import read_input_file, get_versioned_filename

# Setup logging
logger = setup_logging()

# Get configuration
config = get_config()


async def fetch_available_models(api_key: str, is_azure: bool = False) -> List[str]:
    """Fetch available models from OpenAI API or Azure OpenAI."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=conn) as session:
        try:
            if is_azure:
                # For Azure, we can't fetch models dynamically, so we return a predefined list
                return ["gpt-35-turbo", "gpt-4"]  # Add more Azure models as needed
            else:
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        gpt_models = [model['id'] for model in data['data'] if model['id'].startswith('gpt')]
                        return sorted(gpt_models)
                    else:
                        st.error(f"Failed to fetch models: {response.status}")
                        return []
        except Exception as e:
            st.error(f"Error fetching models: {str(e)}")
            return []


def main():
    st.set_page_config(page_title="Ticket Analysis Application", layout="wide")
    st.title("Ticket Analysis Application")

    # Sidebar settings
    with st.sidebar:
        st.title("Settings")
        debug_mode = st.checkbox("Debug Mode", value=False)

        # API Type selection
        api_type = st.selectbox("API Type", ["OpenAI", "Azure OpenAI"],
                                index=0 if config.get('API_TYPE').lower() == 'openai' else 1)
        config.set('API_TYPE', 'openai' if api_type == "OpenAI" else 'azure')

        if config.is_azure_openai:
            config.set('AZURE_OPENAI_API_BASE',
                       st.text_input("Azure OpenAI API Base", value=config.get('AZURE_OPENAI_API_BASE')))
            config.set('AZURE_OPENAI_API_VERSION',
                       st.text_input("Azure OpenAI API Version", value=config.get('AZURE_OPENAI_API_VERSION')))
            config.set('AZURE_OPENAI_API_KEY',
                       st.text_input("Azure OpenAI API Key", value=config.get('AZURE_OPENAI_API_KEY'), type="password"))
            config.set('AZURE_OPENAI_DEPLOYMENT_NAME',
                       st.text_input("Azure OpenAI Deployment Name", value=config.get('AZURE_OPENAI_DEPLOYMENT_NAME')))
            model = config.get('AZURE_OPENAI_DEPLOYMENT_NAME')
        else:
            config.set('OPENAI_API_KEY',
                       st.text_input("OpenAI API Key", value=config.get('OPENAI_API_KEY'), type="password"))
            api_key = config.get('OPENAI_API_KEY')
            available_models = asyncio.run(fetch_available_models(api_key))
            model = st.selectbox("Select Model", available_models,
                                 index=available_models.index(config.get('MODEL')) if config.get(
                                     'MODEL') in available_models else 0)

        config.set('MODEL', model)

        max_tokens = st.number_input("Max Tokens", value=int(config.get('MAX_TOKENS')), min_value=1, max_value=4096)
        config.set('MAX_TOKENS', str(max_tokens))

        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=float(config.get('TEMPERATURE')),
                                step=0.1)
        config.set('TEMPERATURE', str(temperature))

        include_raw_response = st.checkbox("Include Raw Response", value=debug_mode)
        include_explanations = st.checkbox("Include Explanations", value=True)

    # File upload
    uploaded_file = st.file_uploader("Choose an input file", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            df = read_input_file(uploaded_file)
            total_tickets = len(df)
            st.success(f"Input file loaded successfully. Total tickets: {total_tickets}")

            # Column selection
            columns = list(df.columns)
            selected_columns = st.multiselect("Select columns for analysis", columns)

            tracking_index_column = st.selectbox(
                "Select tracking index column",
                [""] + columns,
                index=columns.index("id") + 1 if "id" in columns else 0
            )

            # Analysis type selection
            st.subheader("Analysis Types")

            analysis_options = {
                "Basic Analysis": {
                    "extract_product": "Extract Product",
                    "summarize_ticket": "Summarize Ticket",
                    "ticket_quality": "Ticket Quality",
                    "sentiment_analysis": "Sentiment Analysis"
                },
                "User Analysis": {
                    "user_proficiency_level": "User Proficiency Level",
                    "urgency_perception": "Urgency Perception",
                    "emotion_detection": "Emotion Detection"
                },
                "Impact Analysis": {
                    "potential_impact": "Potential Impact",
                    "information_completeness": "Information Completeness",
                    "resolution_complexity": "Resolution Complexity"
                },
                "Resolution Analysis": {
                    "resolution_appropriateness": "Resolution Appropriateness",
                    "suggested_kb_article": "Suggested KB Article",
                    "expected_resolution_time": "Expected Resolution Time",
                    "next_best_action": "Next Best Action"
                },
                "Advanced Analysis": {
                    "historical_similarity": "Historical Similarity",
                    "potential_root_cause": "Potential Root Cause",
                    "resolution_confidence": "Resolution Confidence",
                    "customer_satisfaction_prediction": "Customer Satisfaction Prediction"
                }
            }

            selected_analysis_types = []
            for category, options in analysis_options.items():
                st.write(f"**{category}**")
                selected = st.multiselect(f"Select {category} types", list(options.values()), key=category)
                selected_analysis_types.extend([k for k, v in options.items() if v in selected])

            if st.button("Start Analysis"):
                if not selected_columns:
                    st.warning("Please select at least one column for analysis.")
                elif not tracking_index_column:
                    st.warning("Please select a tracking index column.")
                elif not selected_analysis_types:
                    st.warning("Please select at least one analysis type.")
                else:
                    run_analysis(df, selected_columns, tracking_index_column, selected_analysis_types,
                                 include_raw_response, include_explanations, debug_mode, config)

        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")
            logger.exception("Error in Streamlit app while processing input file")


async def process_tickets(analyzer, tickets, selected_columns, tracking_index_column, selected_analysis_types,
                          include_explanations):
    async for batch_data in analyzer.analyze_tickets(
            tickets, selected_columns, tracking_index_column, selected_analysis_types, include_explanations
    ):
        yield batch_data


def run_analysis(df: pd.DataFrame, selected_columns: List[str], tracking_index_column: str,
                 selected_analysis_types: List[str], include_raw_response: bool, include_explanations: bool,
                 debug_mode: bool, config: Config):
    try:
        # Initialize the ticket analyzer
        analyzer = AsyncTicketAnalyzer(config)

        # Process tickets in batches
        output_file_prefix = config.get('OUTPUT_FILE_PREFIX', 'analysis')
        output_file = get_versioned_filename(output_file_prefix, config.get('MODEL'))
        tickets = df.to_dict("records")

        if debug_mode:
            tickets = tickets[:10]  # Only process the first 10 tickets in debug mode

        progress_bar = st.progress(0)
        status_text = st.empty()
        error_text = st.empty()
        raw_response_area = st.empty()

        async def process_tickets_async():
            processed_tickets = 0
            total_tickets = len(tickets)

            async for batch_data in process_tickets(analyzer, tickets, selected_columns, tracking_index_column,
                                                    selected_analysis_types, include_explanations):
                batch_results = []
                for ticket, result in zip(batch_data["batch_tickets"], batch_data["batch_results"]):
                    try:
                        if include_raw_response:
                            result["raw_response"] = result.pop("_raw_response", "N/A")
                        batch_results.append(result)
                    except Exception as exc:
                        logger.error(
                            f"Error processing ticket {ticket.get(tracking_index_column, 'Unknown')}: {str(exc)}")
                        batch_results.append({
                            "tracking_index": ticket.get(tracking_index_column, ""),
                            "error": str(exc),
                            "error_type": type(exc).__name__
                        })

                processed_tickets += len(batch_results)
                progress = processed_tickets / total_tickets
                progress_bar.progress(min(progress, 1.0))
                status_text.text(f"Processed {processed_tickets} out of {total_tickets} tickets")

                # Display raw responses in debug mode
                if debug_mode:
                    raw_responses = [result.get("raw_response", "N/A") for result in batch_results]
                    raw_response_area.text_area("Raw Responses", "\n\n".join(raw_responses), height=300)

                # Write batch results to CSV
                try:
                    df_processed = pd.DataFrame(batch_results)
                    df_processed.to_csv(output_file, mode="a", header=not os.path.exists(output_file), index=False)
                    logger.info(f"Batch results written to {output_file}")
                except Exception as csv_error:
                    csv_error_message = f"Error writing results to CSV: {str(csv_error)}"
                    error_text.error(csv_error_message)
                    logger.exception(csv_error_message)

            status_text.text(f"Analysis completed. Processed {processed_tickets} tickets.")
            st.success(f"Analysis completed successfully. Results saved to {output_file}")

            # Provide download button for the results
            if os.path.exists(output_file):
                with open(output_file, "rb") as file:
                    st.download_button(
                        label="Download Results CSV",
                        data=file,
                        file_name=os.path.basename(output_file),
                        mime="text/csv"
                    )
            else:
                st.error(f"Output file {output_file} not found. Unable to provide download.")

        # Run the asynchronous analysis
        asyncio.run(process_tickets_async())

    except Exception as analysis_error:
        error_message = f"An error occurred during analysis: {str(analysis_error)}"
        st.error(error_message)
        logger.exception(error_message)


if __name__ == "__main__":
    main()
