import pandas as pd
from colorama import Fore, Style


def display_menu_options(options: list[str]) -> None:
    for i, option in enumerate(options, start=1):
        print(f"{Fore.BLUE}{i}. {option}{Style.RESET_ALL}")


def get_user_selection(prompt: str, options: list[str]) -> list[str]:
    selected_options = []
    while True:
        indices = input(f"\n{Fore.YELLOW}{prompt}{Style.RESET_ALL}")
        indices = [int(index.strip()) - 1 for index in indices.split(',')]
        selected_options = [options[index] for index in indices if 0 <= index < len(options)]

        print(f"\n{Fore.CYAN}Selected options: {', '.join(selected_options)}{Style.RESET_ALL}")
        confirmation = input(f"{Fore.GREEN}Are these the correct options? (Y/N): {Style.RESET_ALL}")
        if confirmation.upper() == 'Y':
            break
        elif confirmation.upper() == 'N':
            selected_options = []
        else:
            print(f"{Fore.RED}Invalid input. Please enter Y or N.{Style.RESET_ALL}")

    return selected_options


def select_columns(columns: list[str], df: pd.DataFrame) -> tuple[list[str], str]:
    print(f"{Fore.CYAN}Available columns:{Style.RESET_ALL}")
    display_menu_options(columns)

    selected_columns = get_user_selection(
        "Select the columns you want to use for analysis (comma-separated): ", columns)

    # Validate selected columns against DataFrame columns
    invalid_columns = set(selected_columns) - set(df.columns)
    while invalid_columns:
        print(f"\n{Fore.RED}Invalid column(s) selected: {', '.join(invalid_columns)}{Style.RESET_ALL}")
        print("Please select valid columns from the available options.")
        selected_columns = get_user_selection(
            "Select the columns you want to use for analysis (comma-separated): ", columns)
        invalid_columns = set(selected_columns) - set(df.columns)

    tracking_index_column = None
    while True:
        tracking_index = input(
            f"\n{Fore.YELLOW}Select the column to use as the tracking index (or leave blank if not required): {Style.RESET_ALL}")
        if tracking_index.strip() == "":
            break
        try:
            index = int(tracking_index.strip()) - 1
            if 0 <= index < len(columns):
                tracking_index_column = columns[index]

                # Validate tracking index column against DataFrame columns
                if tracking_index_column not in df.columns:
                    print(
                        f"\n{Fore.RED}Invalid tracking index column selected: {tracking_index_column}{Style.RESET_ALL}")
                    print("Please select a valid column from the available options.")
                    continue

                break
            else:
                print(f"{Fore.RED}Invalid tracking index: {index + 1}. Please try again.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Invalid input. Please enter a valid tracking index.{Style.RESET_ALL}")

    return selected_columns, tracking_index_column


def select_analysis_types() -> list[str]:
    analysis_types = ["extract_product", "summarize_ticket", "resolution_appropriateness", "ticket_quality",
                      "sentiment_analysis"]
    print(f"{Fore.CYAN}Available analysis types:{Style.RESET_ALL}")
    display_menu_options(analysis_types)

    selected_analysis_types = get_user_selection(
        "Select the analysis types you want to perform (comma-separated): ", analysis_types)

    return selected_analysis_types
