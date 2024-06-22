from typing import List, Tuple

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def display_menu_options(options: List[str]) -> None:
    table = Table(show_header=False, box=None)
    for i, option in enumerate(options, start=1):
        table.add_row(f"[cyan]{i}.[/cyan]", option)
    console.print(table)


def get_user_selection(prompt: str, options: List[str], allow_multiple: bool = True) -> List[str]:
    while True:
        console.print(f"\n[yellow]{prompt}[/yellow]")
        indices = console.input("Enter your selection (comma-separated numbers): ")
        try:
            if allow_multiple:
                indices = [int(index.strip()) - 1 for index in indices.split(',')]
            else:
                indices = [int(indices.strip()) - 1]

            if all(0 <= index < len(options) for index in indices):
                return [options[index] for index in indices]
            else:
                console.print("[red]Invalid input. Please enter valid indices.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Please enter numbers separated by commas.[/red]")


def select_columns(columns: List[str], df: pd.DataFrame) -> Tuple[List[str], str]:
    console.print(Panel("Column Selection", expand=False))
    console.print("Available columns:")
    display_menu_options(columns)

    selected_columns = get_user_selection(
        "Select the columns you want to use for analysis (comma-separated numbers):",
        columns
    )

    # Validate selected columns against DataFrame columns
    invalid_columns = set(selected_columns) - set(df.columns)
    while invalid_columns:
        console.print(f"\n[red]Invalid column(s) selected: {', '.join(invalid_columns)}[/red]")
        console.print("Please select valid columns from the available options.")
        selected_columns = get_user_selection(
            "Select the columns you want to use for analysis (comma-separated numbers):",
            columns
        )
        invalid_columns = set(selected_columns) - set(df.columns)

    console.print("\nSelect tracking index column:")
    display_menu_options(columns)

    while True:
        tracking_index_column = get_user_selection(
            "Select the column to use as the tracking index:",
            columns,
            allow_multiple=False
        )[0]

        if tracking_index_column in df.columns:
            break
        else:
            console.print(f"[red]Invalid tracking index column selected: {tracking_index_column}[/red]")
            console.print("Please select a valid column from the available options.")

    return selected_columns, tracking_index_column


def select_analysis_types() -> List[str]:
    analysis_categories = {
        "Basic Analysis": [
            "extract_product",
            "summarize_ticket",
            "ticket_quality",
            "sentiment_analysis"
        ],
        "User Analysis": [
            "user_proficiency_level",
            "urgency_perception",
            "emotion_detection"
        ],
        "Impact Analysis": [
            "potential_impact",
            "information_completeness",
            "resolution_complexity"
        ],
        "Resolution Analysis": [
            "resolution_appropriateness",
            "suggested_kb_article",
            "expected_resolution_time",
            "next_best_action"
        ],
        "Advanced Analysis": [
            "historical_similarity",
            "potential_root_cause",
            "resolution_confidence",
            "customer_satisfaction_prediction"
        ]
    }

    selected_analysis_types = []

    console.print(Panel("Analysis Type Selection", expand=False))
    for category, analysis_types in analysis_categories.items():
        console.print(f"\n[cyan]{category}[/cyan]")
        display_menu_options(analysis_types)

        selected_types = get_user_selection(
            f"Select the analysis types you want to perform for {category} (comma-separated numbers):",
            analysis_types
        )
        selected_analysis_types.extend(selected_types)

    return selected_analysis_types


def display_job_overview(df: pd.DataFrame, selected_columns: List[str], tracking_index_column: str,
                         selected_analysis_types: List[str]) -> bool:
    total_rows = len(df)
    total_characters = df[selected_columns].astype(str).apply(lambda x: x.str.len()).sum().sum()

    overview = Table(title="Job Overview", show_header=False, box=None)
    overview.add_row("Total Rows:", str(total_rows))
    overview.add_row("Selected Columns:", ", ".join(selected_columns))
    overview.add_row("Tracking Index Column:", tracking_index_column)
    overview.add_row("Selected Analysis Types:", ", ".join(selected_analysis_types))
    overview.add_row("Total Characters:", str(total_characters))

    console.print(overview)

    while True:
        confirmation = console.input("\n[yellow]Proceed with the analysis? (Y/N): [/yellow]").strip().upper()
        if confirmation == 'Y':
            return True
        elif confirmation == 'N':
            return False
        else:
            console.print("[red]Invalid input. Please enter Y or N.[/red]")