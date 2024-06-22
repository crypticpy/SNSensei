import ssl
import time
import asyncio
import aiohttp
import logging
import json
from typing import List, Dict, Any
import certifi

import tenacity
from app.preprocessor import preprocess_ticket
from app.prompts import generate_prompt
from app.postprocessor import postprocess_output
from app.config import Config, get_config

logger = logging.getLogger(__name__)


class AsyncTicketAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.is_azure = config.is_azure_openai
        self.api_key = config.get('AZURE_OPENAI_API_KEY') if self.is_azure else config.get('OPENAI_API_KEY')
        self.model = config.get('AZURE_OPENAI_DEPLOYMENT_NAME') if self.is_azure else config.get('MODEL')
        self.max_tokens = int(config.get('MAX_TOKENS'))
        self.temperature = float(config.get('TEMPERATURE'))
        self.initial_batch_size = int(config.get('INITIAL_BATCH_SIZE'))
        self.max_batch_size = int(config.get('MAX_BATCH_SIZE'))
        self.batch_size_factor = float(config.get('BATCH_SIZE_FACTOR'))

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=60) + tenacity.wait_random(min=0, max=3),
        retry=tenacity.retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING)
    )
    async def _call_openai_api(self, messages: List[Dict[str, str]]) -> str:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            try:
                if self.is_azure:
                    url = f"{self.config.get('AZURE_OPENAI_API_BASE')}/openai/deployments/{self.model}/chat/completions?api-version={self.config.get('AZURE_OPENAI_API_VERSION')}"
                    headers = {
                        "api-key": self.api_key,
                        "Content-Type": "application/json"
                    }
                else:
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }

                payload = {
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
                if not self.is_azure:
                    payload["model"] = self.model

                async with session.post(url, json=payload, headers=headers, ssl=ssl_context, timeout=30) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
            except aiohttp.ClientResponseError as e:
                logger.error(f"API request failed with status {e.status}: {e.message}")
                raise
            except asyncio.TimeoutError:
                logger.error("API request timed out")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during API call: {str(e)}")
                raise

    def validate_llm_response(self, response: Dict[str, Any], analysis_types: List[str],
                              include_explanations: bool) -> bool:
        required_fields = set(analysis_types)
        if include_explanations:
            required_fields.update(f"{analysis_type}_explanation" for analysis_type in analysis_types)
        response_fields = set(response.keys())
        missing_fields = required_fields - response_fields
        if missing_fields:
            logger.warning(f"LLM response is missing fields: {missing_fields}")
            return False
        return True

    def parse_json_response(self, raw_output: str) -> Dict[str, Any]:
        """
        Attempt to parse the JSON response from the LLM, handling potential irregularities.
        """
        # First, try to parse the entire output as JSON
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            pass

        # If that fails, try to extract JSON from the response
        try:
            json_start = raw_output.index('{')
            json_end = raw_output.rindex('}') + 1
            json_str = raw_output[json_start:json_end]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            pass

        # If JSON extraction fails, attempt to create a structured dict from the output
        structured_output = {}
        lines = raw_output.split('\n')
        current_key = None
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                current_key = key.strip().lower().replace(' ', '_')
                structured_output[current_key] = value.strip()
            elif current_key:
                structured_output[current_key] += ' ' + line.strip()

        if structured_output:
            return structured_output

        # If all parsing attempts fail, raise an exception
        raise ValueError("Failed to parse LLM output into a structured format")

    async def analyze_ticket(self, ticket: Dict[str, Any], columns: List[str],
                             tracking_index_column: str, analysis_types: List[str],
                             include_explanations: bool) -> Dict[str, Any]:
        try:
            preprocessed_ticket = preprocess_ticket(ticket, columns, tracking_index_column)
            prompt = generate_prompt(preprocessed_ticket, columns, analysis_types, include_explanations)

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes help desk tickets and always responds in the proper json format.",
                },
                {"role": "user", "content": prompt},
            ]

            raw_output = await self._call_openai_api(messages)
            logger.info(f"AI response for ticket {preprocessed_ticket.get('tracking_index', '')}: {raw_output}")

            try:
                parsed_output = self.parse_json_response(raw_output)
            except ValueError:
                logger.error(
                    f"Failed to parse LLM output for ticket {preprocessed_ticket.get('tracking_index', '')}")
                return {
                    "tracking_index": preprocessed_ticket.get("tracking_index", ""),
                    "error": "Failed to parse LLM output",
                    "error_type": "ParsingError",
                    "_raw_response": raw_output
                }

            if not self.validate_llm_response(parsed_output, analysis_types, include_explanations):
                logger.warning(f"Invalid LLM response for ticket {preprocessed_ticket.get('tracking_index', '')}")
                return {
                    "tracking_index": preprocessed_ticket.get("tracking_index", ""),
                    "error": "Invalid LLM response",
                    "error_type": "ValidationError",
                    "_raw_response": raw_output
                }

            result = postprocess_output(parsed_output, analysis_types, preprocessed_ticket, include_explanations)
            result["_raw_response"] = raw_output
            logger.debug(f"Postprocessed result: {result}")

            return result

        except Exception as exc:
            logger.error(f"Failed to analyze ticket: {str(exc)}")
            return {
                "tracking_index": preprocessed_ticket.get("tracking_index", ""),
                "error": str(exc),
                "error_type": type(exc).__name__,
                "_raw_response": raw_output if 'raw_output' in locals() else "N/A"
            }

    async def analyze_tickets(self, tickets: List[Dict[str, Any]], columns: List[str],
                              tracking_index_column: str, analysis_types: List[str],
                              include_explanations: bool):
        batch_size = self.initial_batch_size
        total_tickets = len(tickets)

        async def process_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            tasks = [self.analyze_ticket(ticket, columns, tracking_index_column, analysis_types, include_explanations)
                     for ticket in batch]
            return await asyncio.gather(*tasks)

        processed_tickets = 0
        while processed_tickets < total_tickets:
            batch_tickets = tickets[processed_tickets:processed_tickets + batch_size]
            batch_start_time = time.time()
            batch_results = await process_batch(batch_tickets)
            batch_end_time = time.time()
            batch_execution_time = batch_end_time - batch_start_time

            batch_error_count = sum(1 for result in batch_results if "error" in result)
            batch_error_details = [result["error"] for result in batch_results if "error" in result]

            current_batch = (processed_tickets // batch_size) + 1
            total_batches = (total_tickets + batch_size - 1) // batch_size

            processed_tickets += len(batch_tickets)

            yield {
                "batch_tickets": batch_tickets,
                "batch_results": batch_results,
                "batch_size": batch_size,
                "batch_error_count": batch_error_count,
                "batch_error_details": batch_error_details,
                "batch_execution_time": batch_execution_time,
                "current_batch": current_batch,
                "total_batches": total_batches,
            }

            # Adjust batch size based on performance
            if batch_execution_time < 1.0:
                batch_size = min(int(batch_size * self.batch_size_factor), self.max_batch_size)
            elif batch_execution_time > 5.0:
                batch_size = max(int(batch_size / self.batch_size_factor), self.initial_batch_size)

            logger.info(f"Batch {current_batch}/{total_batches} processed. "
                        f"Execution time: {batch_execution_time:.2f}s. "
                        f"New batch size: {batch_size}")


# Example usage
if __name__ == "__main__":
    config = get_config()
    analyzer = AsyncTicketAnalyzer(config)

    # You can add some test code here to verify the analyzer's functionality
    # For example:
    # test_ticket = {...}
    # test_columns = [...]
    # test_analysis_types = [...]
    # result = asyncio.run(analyzer.analyze_ticket(test_ticket, test_columns, "id", test_analysis_types, True))
    # print(result)