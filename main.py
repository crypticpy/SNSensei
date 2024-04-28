import os
import time
from typing import Any

import colorama
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn

from analyzer import TicketAnalyzer
from config import get_config
from logging_config import setup_logging
from menu import select_columns, select_analysis_types
from utils import get_versioned_filename, read_input_file


def main():
    global logger
    colorama.init()

    try:
        # Read configuration from environment variables or a configuration file
        config = get_config()
        api_key = config["api_key"]
        model = config["model"]
        max_tokens = config["max_tokens"]
        temperature = config["temperature"]
        initial_batch_size = config["initial_batch_size"]
        max_batch_size = config["max_batch_size"]
        batch_size_factor = config["batch_size_factor"]
        max_workers = config["max_workers"]
        output_file_prefix = config["output_file_prefix"]

        logger = setup_logging(config)
        logger.info("Configuration loaded successfully.")

        # Read the input file
        df = read_input_file()
        total_tickets = len(df)
        logger.info(f"Input file loaded successfully. Total tickets: {total_tickets}")

        # Prompt the user to select columns for analysis and tracking index
        columns: list[Any] = list(df.columns)
        selected_columns, tracking_index_column = select_columns(columns, df)
        logger.info(f"Selected columns: {', '.join(selected_columns)}")
        logger.info(f"Tracking index column: {tracking_index_column}")

        # Prompt the user to select analysis types
        selected_analysis_types = select_analysis_types()

        # Initialize the ticket analyzer
        analyzer = TicketAnalyzer(api_key, model, max_tokens, temperature, initial_batch_size=initial_batch_size,
                                  max_batch_size=max_batch_size, batch_size_factor=batch_size_factor)

        # Process tickets in batches
        output_file = get_versioned_filename(output_file_prefix)

        tickets = df.to_dict("records")

        console = Console()

        with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TextColumn("[bold green]{task.completed}/{task.total}"),
                TextColumn("[bold yellow]{task.fields[tickets_per_second]:.2f} tickets/s"),
                TextColumn("[bold cyan]Batch: {task.fields[current_batch]}/{task.fields[total_batches]}"),
                TextColumn("[bold magenta]Workers: {task.fields[current_workers]}"),
                TimeRemainingColumn(),
                console=console,
                transient=True,
        ) as progress:
            total_batches = total_tickets // initial_batch_size + 1
            task = progress.add_task(
                "[cyan]Analyzing Tickets...",
                total=total_tickets,
                tickets_per_second=0.0,
                current_batch=1,
                total_batches=total_batches,
                current_workers=max_workers,
            )

            processed_tickets = 0
            start_time = time.time()

            for batch, batch_size, num_workers in analyzer.analyze_tickets(tickets, selected_columns,
                                                                           tracking_index_column,
                                                                           selected_analysis_types, max_workers):
                progress.update(task, advance=len(batch))
                processed_tickets += len(batch)

                # Update tickets per second
                elapsed_time = time.time() - start_time
                tickets_per_second = processed_tickets / elapsed_time if elapsed_time > 0 else 0
                progress.update(task, tickets_per_second=tickets_per_second)

                # Update current batch and workers
                current_batch = processed_tickets // initial_batch_size + 1
                progress.update(task, current_batch=current_batch, current_workers=num_workers)

                # Append the processed tickets to the output CSV file
                df_processed = pd.DataFrame(batch)
                df_processed.to_csv(output_file, mode="a", header=not os.path.exists(output_file), index=False)

        console.print(Panel("[bold green]Analysis Complete[/bold green]", expand=False))

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise


if __name__ == "__main__":
    main()
