import logging
import os
import json
import asyncio
from azure.storage.blob import BlobServiceClient
from shared.promote import trigger_merge_to_alpha

async def main(mytimer):
    logging.info("⏱️ Auto promote task started")

    connection_string = os.getenv("AzureWebJobsStorage")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container = blob_service.get_container_client("models")

    max_attempts = 30
    delay = 5  # secondi

    for attempt in range(max_attempts):
        logging.info(f"🔁 Tentativo {attempt+1}/{max_attempts}")
        ready_count = 0

        for wine_type in ['red', 'white']:
            try:
                # controlla status_{wine_type}.json
                status_blob = container.get_blob_client(f"status_{wine_type}.json")
                if not status_blob.exists():
                    continue

                data = status_blob.download_blob().readall().decode('utf-8')
                status = json.loads(data).get("status", "training")
                if status == "ready":
                    ready_count += 1
            except Exception as e:
                logging.warning(f"Errore controllando status {wine_type}: {str(e)}")

        if ready_count > 0:
            logging.info("✅ Almeno un modello è pronto. Trigger merge.")
            trigger_merge_to_alpha()
            return

        await asyncio.sleep(delay)

    logging.warning("❌ Timeout: nessun modello pronto dopo polling")