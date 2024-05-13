import os
import time
from typing import Any

import colorama
import pandas as pd
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, SpinnerColumn
from rich.live import Live

from app.analyzer import TicketAnalyzer
from app.config import get_config
from app.logging_config import setup_logging
from app.menu import select_columns, select_analysis_types
from app.utils import get_versioned_filename, read_input_file


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

        progress = Progress(
            SpinnerColumn(),
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
        )

        total_batches = total_tickets // initial_batch_size + (1 if total_tickets % initial_batch_size > 0 else 0)
        task = progress.add_task(
            "[cyan]Analyzing Tickets...",
            total=total_tickets,
            tickets_per_second=0.0,
            current_batch=1,
            total_batches=total_batches,
            current_workers=max_workers,
        )

        start_time = time.time()
        update_interval = 0.1  # Update every 0.1 seconds

        with Live(console=console, refresh_per_second=10) as live:
            for batch, batch_size, num_workers, processed_tickets, total_batches, current_batch, error_count, batch_execution_time, batch_error_details, capacity_messages in analyzer.analyze_tickets(
                    tickets, selected_columns, tracking_index_column, selected_analysis_types, max_workers):
                progress.update(task, advance=len(batch))

                # Update tickets per second
                elapsed_time = time.time() - start_time
                tickets_per_second = processed_tickets / elapsed_time if elapsed_time > 0 else 0
                progress.update(task, tickets_per_second=tickets_per_second)

                # Update current batch, total batches, and workers
                progress.update(task, current_batch=current_batch, total_batches=total_batches, current_workers=num_workers)

                # Append the processed tickets to the output CSV file
                df_processed = pd.DataFrame(batch)
                os.makedirs('output', exist_ok=True)
                df_processed.to_csv(output_file, mode="a", header=not os.path.exists(output_file), index=False)

                # Update the job status area
                time_remaining = progress.tasks[task].time_remaining
                time_remaining_str = str(time_remaining) if time_remaining is not None else "Calculating..."
                job_status = f"Total Tickets: {total_tickets}\n" \
                             f"Processed Tickets: {processed_tickets}\n" \
                             f"Remaining Tickets: {total_tickets - processed_tickets}\n" \
                             f"Current Batch: {current_batch}/{total_batches}\n" \
                             f"Batch Size: {batch_size}\n" \
                             f"Number of Workers: {num_workers}\n" \
                             f"Tickets per Second: {tickets_per_second:.2f}\n" \
                             f"Time Remaining: {time_remaining_str}\n"

                # Update the batch completion messages
                batch_message = f"Batch {current_batch} Completed\n" \
                                f"Batch execution time: {batch_execution_time:.2f} seconds\n" \
                                f"Average ticket processing time: {batch_execution_time / len(batch):.2f} seconds\n" \
                                f"Error count: {error_count}\n" \
                                f"Batch saved successfully\n"

                # Summarize error messages
                error_summary = {}
                for error_detail in batch_error_details:
                    error_summary[error_detail] = error_summary.get(error_detail, 0) + 1

                error_message = "No errors detected."
                if error_count > 0:
                    error_message = f"Errors encountered in batch {current_batch}:\n"
                    for error_detail, count in error_summary.items():
                        error_message += f"- {error_detail} (Occurred {count} times)\n"
                    error_message += f"Total error count: {error_count}\n"

                # Create a new Columns object with the updated panels
                layout = Columns(
                    [
                        Panel(job_status, title="Job Status", expand=False),
                        Panel(batch_message, title="Batch Completion", expand=False),
                        Panel(error_message, title="Error Messages", expand=False),
                        Panel("\n".join(capacity_messages[-5:]), title="Capacity Adjustments", expand=False)
                    ],
                    expand=False,
                )

                live.update(layout)  # Update the layout in place

                time.sleep(update_interval)  # Sleep for the update interval to provide real-time updates

            live.stop()  # Stop the live display before printing the final completion panel
            console.print(Panel("Analysis Complete", expand=False))

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise

    finally:
        colorama.deinit()


if __name__ == "__main__":
    main()









