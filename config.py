import os

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def get_config():
    """Returns the configuration for the application."""
    api_key = os.getenv("OPENAI_API_KEY")
    azure_api_key = os.getenv("AZURE_API_KEY")

    if azure_api_key:
        # Use Azure configuration if available
        config = {
            "api_type": "azure",
            "api_key": azure_api_key,
            "api_base": "https://your_azure_api_base_url/",
            "deployment_name": "your_azure_deployment_name",
            "model": "your_azure_model_name",
            "max_tokens": 300,
            "temperature": 0.1,
            "batch_size": 100,
            "initial_batch_size": 10,
            "max_batch_size": 100,
            "batch_size_factor": 2.0,
            "max_workers": 50,  # Number of concurrent workers for parallel processing
            "output_file_prefix": "processed_tickets",
            "include_raw_response": True,
        }
    elif api_key:
        # Use OpenAI configuration
        config = {
            "api_type": "openai",
            "api_key": api_key,
            "model": "gpt-3.5-turbo-0125",  # Update the model to "gpt-4" for better performance
            "max_tokens": 300,
            "temperature": 0.1,
            "batch_size": 100,
            "initial_batch_size": 10,
            "max_batch_size": 100,
            "batch_size_factor": 2.0,
            "max_workers": 50,  # Number of concurrent workers for parallel processing
            "output_file_prefix": "processed_tickets",
            "include_raw_response": True,
        }
    else:
        raise ValueError("No valid API key found in the environment variables.")

    config["log_level"] = "INFO"
    config["log_format"] = "%(asctime)s - %(levelname)s - %(message)s"

    return config