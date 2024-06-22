import asyncio
import os
import time
from typing import List, Dict, Any

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Confirm, Prompt

from app.analyzer import AsyncTicketAnalyzer
from app.config import get_config
from app.logging_config import setup_logging
from app.menu import select_columns, select_analysis_types
from app.utils import get_versioned_filename, read_input_file, calculate_statistics, display_dataframe_info

console = Console()
logger = setup_logging()


async def process_batch(
        analyzer: AsyncTicketAnalyzer,
        batch: List[Dict[str, Any]],
        columns: List[str],
        tracking_index_column: str,
        analysis_types: List[str],
        include_explanations: bool
) -> List[Dict[str, Any]]:
    results = []
    for ticket in batch:
        try:
            result = await analyzer.analyze_ticket(ticket, columns, tracking_index_column, analysis_types,
                                                   include_explanations)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing ticket {ticket.get(tracking_index_column, 'Unknown')}: {str(e)}")
            results.append({
                "tracking_index": ticket.get(tracking_index_column, ""),
                "error": str(e),
                "error_type": type(e).__name__
            })
    return results


async def main():
    console.print(Panel.fit("Welcome to StreamSensei", style="bold magenta"))

    try:
        # Read configuration
        config = get_config()
        logger.info("Configuration loaded successfully.")

        # Read the input file
        console.print("\n[bold cyan]Step 1: Select Input File[/bold cyan]")
        df = read_input_file()
        total_tickets = len(df)
        logger.info(f"Input file loaded successfully. Total tickets: {total_tickets}")

        # Display dataframe info
        display_dataframe_info(df)

        # Select columns and analysis types
        console.print("\n[bold cyan]Step 2: Select Columns for Analysis[/bold cyan]")
        columns: List[str] = list(df.columns)
        selected_columns, tracking_index_column = select_columns(columns, df)

        console.print("\n[bold cyan]Step 3: Select Analysis Types[/bold cyan]")
        selected_analysis_types = select_analysis_types()

        # Ask user if they want to include explanations
        include_explanations = Confirm.ask("\nDo you want to include explanations in the analysis?", default=True)

        # Display job overview and get confirmation
        console.print("\n[bold cyan]Job Overview:[/bold cyan]")
        stats = calculate_statistics(df)
        for key, value in stats.items():
            if isinstance(value, list):
                console.print(f"  {key}: {', '.join(value)}")
            else:
                console.print(f"  {key}: {value}")
        console.print(f"\nSelected Columns: {', '.join(selected_columns)}")
        console.print(f"Tracking Index Column: {tracking_index_column}")
        console.print(f"Selected Analysis Types: {', '.join(selected_analysis_types)}")
        console.print(f"Include Explanations: {'Yes' if include_explanations else 'No'}")

        if not Confirm.ask("\nDo you want to proceed with the analysis?"):
            console.print("Analysis cancelled. Exiting...")
            return

        # Initialize the ticket analyzer
        analyzer = AsyncTicketAnalyzer(config)

        # Process tickets
        output_file = get_versioned_filename(config.output_file_prefix, config.model)
        tickets = df.to_dict("records")

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
                console=console
        ) as progress:
            analyze_task = progress.add_task("[cyan]Analyzing tickets...", total=total_tickets)

            processed_tickets = 0
            start_time = time.time()

            async for batch_data in analyzer.analyze_tickets(
                    tickets, selected_columns, tracking_index_column, selected_analysis_types, include_explanations
            ):
                batch_results = batch_data["batch_results"]
                batch_size = batch_data["batch_size"]

                processed_tickets += batch_size
                progress.update(analyze_task, advance=batch_size)

                # Write results to CSV
                df_processed = pd.DataFrame(batch_results)
                df_processed.to_csv(output_file, mode="a", header=not os.path.exists(output_file), index=False)

                # Update progress information
                elapsed_time = time.time() - start_time
                tickets_per_second = processed_tickets / elapsed_time if elapsed_time > 0 else 0
                progress.update(analyze_task,
                                description=f"[cyan]Analyzing tickets... ({tickets_per_second:.2f} tickets/s)")

        console.print(f"\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {output_file}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {str(e)}")
        console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    asyncio.run(main())