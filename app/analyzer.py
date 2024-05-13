import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

from openai import OpenAI
from requests.exceptions import HTTPError

from app.preprocessor import preprocess_ticket
from app.prompts import generate_prompt

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, max_failures: int, reset_timeout: int):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()

    def is_open(self):
        if self.failures >= self.max_failures:
            if time.time() - self.last_failure_time < self.reset_timeout:
                return True
            else:
                self.failures = 0
        return False


class TicketAnalyzer:
    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float, max_retries: int = 5,
                 initial_delay: float = 1.0, backoff_factor: float = 2.0, initial_batch_size: int = 10,
                 max_batch_size: int = 100, batch_size_factor: float = 2.0):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.initial_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size
        self.batch_size_factor = batch_size_factor
        self.num_workers = 1
        self.circuit_breaker = CircuitBreaker(max_failures=5, reset_timeout=300)

    @staticmethod
    def postprocess_output(output: str, analysis_types: List[str]) -> Dict:
        try:
            output = output.strip().replace('\n', '').replace('\r', '')
            analyzed_data = json.loads(output)

            result = {}

            if "extract_product" in analysis_types:
                product = analyzed_data.get("product", "").strip()
                result["product"] = product if product and product.lower() != "n/a" else ""
                result["product_explanation"] = analyzed_data.get("product_explanation", "").strip()

            if "summarize_ticket" in analysis_types:
                summary = analyzed_data.get("summary", "").strip()
                result["summary"] = summary if summary else ""
                result["summary_explanation"] = analyzed_data.get("summary_explanation", "").strip()

            if "resolution_appropriateness" in analysis_types:
                resolution_appropriate = analyzed_data.get("resolution_appropriate", "N/A")
                result["resolution_appropriate"] = resolution_appropriate
                result["resolution_explanation"] = analyzed_data.get("resolution_explanation", "").strip()

            if "ticket_quality" in analysis_types:
                ticket_quality = analyzed_data.get("ticket_quality", "").strip().lower()
                result["ticket_quality"] = ticket_quality if ticket_quality in ["good", "fair", "poor"] else ""
                result["quality_explanation"] = analyzed_data.get("quality_explanation", "").strip()

            if "sentiment_analysis" in analysis_types:
                sentiment = analyzed_data.get("sentiment", "").strip().lower()
                result["sentiment"] = sentiment if sentiment in ["positive", "negative", "neutral", "n/a"] else ""
                result["sentiment_explanation"] = analyzed_data.get("sentiment_explanation", "").strip()

            # Capture any excess or unexpected response
            excess_response = {key: value for key, value in analyzed_data.items() if key not in result}
            if excess_response:
                result["excess_response"] = excess_response

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {str(e)}\nOutput: {output}")
            return {analysis_type: "" for analysis_type in analysis_types}

    def analyze_ticket(self, ticket: Dict, columns: List[str], tracking_index_column: str, analysis_types: List[str]) -> \
            Tuple[Dict, str, Dict]:
        """Analyzes a single ticket using OpenAI API."""
        if self.circuit_breaker.is_open():
            logger.error("Circuit breaker is open. Aborting retries.")
            return {}, "", {}

        preprocessed_ticket = preprocess_ticket(ticket, columns, tracking_index_column)
        prompt = generate_prompt(preprocessed_ticket, columns, analysis_types)

        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes help desk tickets and always responds in the proper json format."},
            {"role": "user", "content": prompt}
        ]

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                output = response.choices[0].message.content.strip()
                analyzed_ticket = self.postprocess_output(output, analysis_types)
                return preprocessed_ticket, output, analyzed_ticket
            except HTTPError as e:
                if e.response.status_code in [429, 503]:
                    wait_time = self.initial_delay * (self.backoff_factor ** attempt)
                    wait_time += random.uniform(0, self.initial_delay)  # Adding jitter
                    logger.warning(
                        f"API rate limit or server error encountered. Waiting for {wait_time:.2f} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error occurred: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Failed to analyze ticket: {str(e)}")
                raise
            finally:
                time.sleep(1)  # Throttle requests

        logger.error(f"Max retries exceeded for ticket analysis.")
        self.circuit_breaker.record_failure()
        return preprocessed_ticket, "", {}

    def analyze_tickets(self, tickets: List[Dict], columns: List[str], tracking_index_column: str,
                        analysis_types: List[str], max_workers: int = 50):
        num_workers = min(max_workers, self.initial_batch_size)
        batch_size = self.initial_batch_size
        error_count = 0
        total_tickets = len(tickets)
        max_batch_size = min(self.max_batch_size, len(tickets))
        self.num_workers = num_workers
        processed_tickets = 0
        capacity_messages = []

        def process_batch(futures):
            batch_start_time = time.time()
            batch = []
            batch_error_count = 0
            batch_error_details = []
            for future in as_completed(futures):
                try:
                    preprocessed_ticket, raw_response, analyzed_ticket = future.result()
                    batch.append((preprocessed_ticket, raw_response, analyzed_ticket))
                except Exception as exc:
                    logger.error(f'Ticket analysis generated an exception: {str(exc)}')
                    batch_error_count += 1
                    batch_error_details.append(str(exc))
            batch_end_time = time.time()
            batch_execution_time = batch_end_time - batch_start_time
            return batch, batch_error_count, batch_error_details, batch_execution_time

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for ticket in tickets:
                if self.circuit_breaker.is_open():
                    logger.error("Circuit breaker is open. Stopping ticket analysis.")
                    break

                future = executor.submit(self.analyze_ticket, ticket, columns, tracking_index_column,
                                         analysis_types)
                futures.append(future)
                if len(futures) >= batch_size:
                    batch, batch_error_count, batch_error_details, batch_execution_time = process_batch(futures)
                    processed_tickets += len(batch)
                    total_batches = total_tickets // batch_size + (1 if total_tickets % batch_size > 0 else 0)
                    current_batch = (processed_tickets - 1) // batch_size + 1

                    logger.info(f"Batch execution time: {batch_execution_time:.2f} seconds")
                    logger.info(f"Error count: {batch_error_count}")
                    logger.info(f"Batch size: {batch_size}")
                    logger.info(f"Number of workers: {num_workers}")
                    logger.info(f"Current batch: {current_batch}/{total_batches}")

                    error_count += batch_error_count

                    if batch_error_count == 0:
                        if batch_execution_time < 60.0 and batch_size < max_batch_size:
                            batch_size = min(int(batch_size * self.batch_size_factor), max_batch_size)
                            num_workers = min(int(num_workers * self.batch_size_factor), batch_size, max_workers)
                            if batch_size >= 100 and num_workers < 20:
                                num_workers = min(20, batch_size, max_workers)
                            total_batches = total_tickets // batch_size + (1 if total_tickets % batch_size > 0 else 0)
                            capacity_messages.append(f"[bold green]Low error rate, increasing workers and batch size to {num_workers} and {batch_size} respectively.")
                        elif batch_execution_time > 90.0 and batch_size > self.initial_batch_size:
                            batch_size = max(int(batch_size / self.batch_size_factor), self.initial_batch_size)
                            num_workers = max(int(num_workers / self.batch_size_factor), 1)
                            total_batches = total_tickets // batch_size + (1 if total_tickets % batch_size > 0 else 0)
                            capacity_messages.append(f"[bold red]High error rate, decreasing workers and batch size to {num_workers} and {batch_size} respectively.")
                    else:
                        batch_size = max(int(batch_size / self.batch_size_factor), self.initial_batch_size)
                        num_workers = max(int(num_workers / self.batch_size_factor), 1)
                        total_batches = total_tickets // batch_size + (1 if total_tickets % batch_size > 0 else 0)
                        capacity_messages.append(f"[bold red]High error rate, decreasing workers and batch size to {num_workers} and {batch_size} respectively.")

                    self.num_workers = num_workers
                    yield batch, batch_size, num_workers, processed_tickets, total_batches, current_batch, batch_error_count, batch_execution_time, batch_error_details, capacity_messages
                    futures = []

            if futures:
                batch, batch_error_count, batch_error_details, batch_execution_time = process_batch(futures)
                processed_tickets += len(batch)
                current_batch = (processed_tickets - 1) // batch_size + 1

                error_count += batch_error_count

                yield batch, batch_size, num_workers, processed_tickets, total_batches, current_batch, batch_error_count, batch_execution_time, batch_error_details, capacity_messages

