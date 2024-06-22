import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

import pandas as pd
from rich.console import Console
from rich.table import Table
import streamlit as st

console = Console()

def get_versioned_filename(output_file_prefix: str, model: str, extension: str = "csv") -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_name = model.replace('-', '_')  # Replace hyphens with underscores for filename
    version = 1
    os.makedirs("output", exist_ok=True)
    while True:
        output_file = f"output/{output_file_prefix}_{model_name}_{timestamp}_v{version}.{extension}"
        if not os.path.exists(output_file):
            return output_file
        version += 1

def read_input_file(file_input: Optional[Union[str, st.runtime.uploaded_file_manager.UploadedFile]] = None) -> pd.DataFrame:
    """
    Read an input file (CSV or Excel) and return a pandas DataFrame.

    Args:
        file_input (Optional[Union[str, st.runtime.uploaded_file_manager.UploadedFile]]):
            Path to the input file or UploadedFile object. If None, prompts user to select a file.

    Returns:
        pd.DataFrame: The data from the input file.

    Raises:
        FileNotFoundError: If no suitable input files are found.
        ValueError: If an unsupported file type is selected.
    """
    if file_input is None:
        input_files = [file for file in os.listdir(".") if file.endswith((".csv", ".xlsx", ".xls"))]
        if not input_files:
            raise FileNotFoundError("No CSV or Excel files found in the current directory.")

        if len(input_files) == 1:
            file_path = input_files[0]
        else:
            console.print("Available input files:")
            table = Table(show_header=False, box=None)
            for i, file in enumerate(input_files, start=1):
                table.add_row(f"[cyan]{i}.[/cyan]", file)
            console.print(table)

            while True:
                try:
                    file_index = int(console.input("Select the input file number: ")) - 1
                    if 0 <= file_index < len(input_files):
                        file_path = input_files[file_index]
                        break
                    else:
                        console.print("[red]Invalid file number. Please try again.[/red]")
                except ValueError:
                    console.print("[red]Invalid input. Please enter a number.[/red]")

        return read_file(file_path)
    elif isinstance(file_input, str):
        return read_file(file_input)
    elif isinstance(file_input, st.runtime.uploaded_file_manager.UploadedFile):
        return read_uploaded_file(file_input)
    else:
        raise ValueError("Unsupported input type. Expected string path or UploadedFile object.")

def read_file(file_path: str) -> pd.DataFrame:
    """Read a file from a given path."""
    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    elif file_path.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

def read_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Read an uploaded file from Streamlit."""
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")

def save_to_csv(data: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save data to a CSV file.

    Args:
        data (List[Dict[str, Any]]): The data to save.
        output_file (str): The path to the output CSV file.
    """
    df = pd.DataFrame(data)

    # Ensure all columns are present, fill with NaN if missing
    all_columns = set()
    for item in data:
        all_columns.update(item.keys())

    for column in all_columns:
        if column not in df.columns:
            df[column] = pd.NA

    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Data saved to {output_file}")

    # Print the first few rows for debugging
    print(df.head())

def calculate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate basic statistics for a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        Dict[str, Any]: A dictionary containing basic statistics.
    """
    stats = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": df.select_dtypes(include=['int64', 'float64']).columns.tolist(),
        "categorical_columns": df.select_dtypes(include=['object', 'category']).columns.tolist(),
        "missing_values": df.isnull().sum().to_dict()
    }
    return stats

def display_dataframe_info(df: pd.DataFrame) -> None:
    """
    Display information about a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
    """
    console.print("\n[bold]DataFrame Information:[/bold]")
    console.print(f"Shape: {df.shape}")
    console.print("\nColumn Types:")
    for col, dtype in df.dtypes.items():
        console.print(f"  {col}: {dtype}")

    console.print("\nMissing Values:")
    for col, count in df.isnull().sum().items():
        if count > 0:
            console.print(f"  {col}: {count}")

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> List[str]:
    """
    Validate a DataFrame against a list of required columns.

    Args:
        df (pd.DataFrame): The input DataFrame.
        required_columns (List[str]): List of required column names.

    Returns:
        List[str]: List of missing column names, if any.
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    return missing_columns

# Example usage
if __name__ == "__main__":
    # Test get_versioned_filename
    print(get_versioned_filename("test_output"))

    # Test read_input_file
    try:
        df = read_input_file()
        print("Successfully read input file.")
        display_dataframe_info(df)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    # Test calculate_statistics
    if 'df' in locals():
        stats = calculate_statistics(df)
        print("\nDataFrame Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # Test validate_dataframe
    required_cols = ['id', 'description', 'category']
    if 'df' in locals():
        missing_cols = validate_dataframe(df, required_cols)
        if missing_cols:
            print(f"\nMissing required columns: {missing_cols}")
        else:
            print("\nAll required columns are present.")

    # Test save_to_csv
    if 'df' in locals():
        sample_data = df.head(5).to_dict('records')
        save_to_csv(sample_data, "sample_output.csv")
