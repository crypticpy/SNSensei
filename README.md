# StreamSensei

StreamSensei is an advanced ticket analysis tool designed to process and analyze large volumes of help desk tickets efficiently. It uses AI-powered analysis to extract insights, categorize issues, and provide summaries of ticket content.

## Features

- Asynchronous processing of large ticket datasets
- Customizable analysis types
- Support for both OpenAI and Azure OpenAI APIs
- Interactive command-line interface
- Streamlit web application for easy use
- Detailed logging and error handling
- Configurable output formats

## Prerequisites

- Python 3.10+
- OpenAI API key or Azure OpenAI API access

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/StreamSensei.git
   cd StreamSensei
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   Create a `.env` file in the root directory and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   # Or for Azure OpenAI:
   # AZURE_OPENAI_API_KEY=your_azure_openai_api_key
   # AZURE_OPENAI_API_BASE=your_azure_openai_endpoint
   # AZURE_OPENAI_API_VERSION=your_api_version
   ```

## Usage

### Command Line Interface

Run the main script:

```
python main.py
```

Follow the interactive prompts to:
1. Select your input file
2. Choose columns for analysis
3. Select analysis types
4. Review job details and confirm execution

### Streamlit Web Application

To run the Streamlit app:

```
streamlit run streamlit_app.py
```

Navigate to the provided local URL in your web browser to use the graphical interface.

## Configuration

You can modify the `config.py` file to adjust various settings such as:

- API type (OpenAI or Azure)
- Model selection
- Batch processing parameters
- Output file naming conventions

## Project Structure

- `main.py`: Command-line interface for the application
- `streamlit_app.py`: Streamlit web application
- `app/`: Core application logic
  - `analyzer.py`: Ticket analysis implementation
  - `config.py`: Configuration management
  - `logging_config.py`: Logging setup
  - `menu.py`: CLI menu functions
  - `postprocessor.py`: Output processing
  - `preprocessor.py`: Input data preprocessing
  - `prompts.py`: AI prompt generation
  - `utils.py`: Utility functions
- `tests/`: Unit tests

## Contributing

Contributions to StreamSensei are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
