import os
from datetime import datetime


import pandas as pd


def get_versioned_filename(output_file_prefix: str) -> str:
    """Generates a versioned filename based on the output file prefix."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    version = 1
    output_file = f"{output_file_prefix}_{timestamp}_v{version}.csv"
    while os.path.exists(output_file):
        version += 1
        output_file = f"{output_file_prefix}_{timestamp}_v{version}.csv"
    return output_file


def read_input_file() -> pd.DataFrame:
    input_files = [file for file in os.listdir(".") if file.endswith((".csv", ".xlsx", ".xls"))]
    if not input_files:
        raise FileNotFoundError("No CSV or XLSX files found in the application directory.")

    if len(input_files) == 1:
        input_file = input_files[0]
    else:
        print("Available input files:")
        for i, file in enumerate(input_files, start=1):
            print(f"{i}. {file}")

        while True:
            file_index = input("Select the input file you want to use: ")
            try:
                index = int(file_index.strip()) - 1
                if 0 <= index < len(input_files):
                    input_file = input_files[index]
                    break
                else:
                    print(f"Invalid file index: {index + 1}. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a valid file index.")

    if input_file.endswith(".csv"):
        return pd.read_csv(input_file)
    elif input_file.endswith((".xlsx", ".xls")):
        return pd.read_excel(input_file)
