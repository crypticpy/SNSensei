import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import pandas as pd
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient
from azure.core.exceptions import AzureError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.analyzer import AsyncTicketAnalyzer
from app.config import get_config
from app.utils import read_input_file, get_versioned_filename

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Azure configurations
STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME")
COSMOS_DB_URL = os.environ.get("AZURE_COSMOS_DB_URL")
COSMOS_DB_NAME = os.environ.get("AZURE_COSMOS_DB_NAME")
COSMOS_DB_CONTAINER_NAME = os.environ.get("AZURE_COSMOS_DB_CONTAINER_NAME")
LOG_ANALYTICS_WORKSPACE_ID = os.environ.get("AZURE_LOG_ANALYTICS_WORKSPACE_ID")

# Use DefaultAzureCredential for authentication
credential = DefaultAzureCredential()

class AzureBatchProcessor:
    def __init__(self):
        self.config = get_config()
        self.analyzer = AsyncTicketAnalyzer(self.config)
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=credential
        )
        self.cosmos_client = CosmosClient(COSMOS_DB_URL, credential=credential)
        self.database = self.cosmos_client.get_database_client(COSMOS_DB_NAME)
        self.container = self.database.get_container_client(COSMOS_DB_CONTAINER_NAME)
        self.logs_client = LogsIngestionClient(
            endpoint=f"https://{LOG_ANALYTICS_WORKSPACE_ID}.ods.opinsights.azure.com",
            credential=credential
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def process_ticket(self, ticket: Dict[str, Any], columns: List[str], tracking_index_column: str, analysis_types: List[str]) -> Dict[str, Any]:
        try:
            result = await self.analyzer.analyze_ticket(ticket, columns, tracking_index_column, analysis_types, include_explanations=True)
            return result
        except Exception as e:
            logger.error(f"Error processing ticket {ticket.get(tracking_index_column, 'Unknown')}: {str(e)}")
            return {
                "tracking_index": ticket.get(tracking_index_column, ""),
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def process_batch(self, tickets: List[Dict[str, Any]], columns: List[str], tracking_index_column: str, analysis_types: List[str]) -> List[Dict[str, Any]]:
        tasks = [self.process_ticket(ticket, columns, tracking_index_column, analysis_types) for ticket in tickets]
        return await asyncio.gather(*tasks)

    def get_new_tickets(self, last_processed_time: datetime) -> pd.DataFrame:
        query = f"SELECT * FROM c WHERE c._ts >= {int(last_processed_time.timestamp())}"
        items = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return pd.DataFrame(items)

    def update_last_processed_time(self, new_time: datetime):
        self.container.upsert_item({
            "id": "last_processed_time",
            "timestamp": new_time.isoformat()
        })

    def upload_results_to_blob(self, results: List[Dict[str, Any]], filename: str):
        blob_client = self.blob_service_client.get_blob_client(container=STORAGE_CONTAINER_NAME, blob=filename)
        df = pd.DataFrame(results)
        csv_data = df.to_csv(index=False)
        blob_client.upload_blob(csv_data, overwrite=True)

    def log_to_azure_monitor(self, message: str, log_type: str = "BatchProcessorLogs"):
        self.logs_client.upload(
            rule_id=LOG_ANALYTICS_WORKSPACE_ID,
            stream_name=log_type,
            logs=[{
                "TimeGenerated": datetime.utcnow().isoformat(),
                "Message": message
            }]
        )

    async def run_batch_process(self):
        try:
            logger.info("Starting batch process")
            self.log_to_azure_monitor("Starting batch process")

            # Get the last processed time
            last_processed_item = next(self.container.query_items(
                query="SELECT * FROM c WHERE c.id = 'last_processed_time'",
                enable_cross_partition_query=True
            ), None)
            last_processed_time = datetime.fromisoformat(last_processed_item['timestamp']) if last_processed_item else datetime.utcnow() - timedelta(days=1)

            # Get new tickets
            new_tickets = self.get_new_tickets(last_processed_time)
            logger.info(f"Found {len(new_tickets)} new tickets to process")
            self.log_to_azure_monitor(f"Found {len(new_tickets)} new tickets to process")

            if new_tickets.empty:
                logger.info("No new tickets to process")
                self.log_to_azure_monitor("No new tickets to process")
                return

            # Process tickets
            columns = list(new_tickets.columns)
            tracking_index_column = "id"  # Assuming 'id' is the tracking index column
            analysis_types = ["extract_product", "summarize_ticket", "sentiment_analysis"]  # Add more as needed

            batch_size = 100  # Adjust based on your needs
            results = []

            for i in range(0, len(new_tickets), batch_size):
                batch = new_tickets.iloc[i:i+batch_size].to_dict('records')
                batch_results = await self.process_batch(batch, columns, tracking_index_column, analysis_types)
                results.extend(batch_results)
                logger.info(f"Processed batch {i//batch_size + 1}")
                self.log_to_azure_monitor(f"Processed batch {i//batch_size + 1}")

            # Upload results to blob storage
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"ticket_analysis_results_{timestamp}.csv"
            self.upload_results_to_blob(results, filename)
            logger.info(f"Uploaded results to blob storage: {filename}")
            self.log_to_azure_monitor(f"Uploaded results to blob storage: {filename}")

            # Update last processed time
            self.update_last_processed_time(datetime.utcnow())

            logger.info("Batch process completed successfully")
            self.log_to_azure_monitor("Batch process completed successfully")

        except AzureError as ae:
            logger.error(f"Azure-specific error occurred: {str(ae)}")
            self.log_to_azure_monitor(f"Azure-specific error occurred: {str(ae)}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            self.log_to_azure_monitor(f"An unexpected error occurred: {str(e)}")

def main():
    processor = AzureBatchProcessor()
    asyncio.run(processor.run_batch_process())

if __name__ == "__main__":
    main()