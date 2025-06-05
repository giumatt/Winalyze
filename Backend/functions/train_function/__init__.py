import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_and_save_model
from datetime import datetime, timezone
import asyncio

async def main(mytimer: func.TimerRequest,
              modelOutput: func.Out[bytes],
              scalerOutput: func.Out[bytes],
              cleanedOutput: func.Out[bytes]) -> None:
    logging.info('Train function triggered by timer')

    try:
        # Connessione al blob storage
        connection_string = os.environ["AzureWebJobsStorage"]
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")

            # Lista dei file da processare
            files_to_process = ['uploaded_red.csv', 'uploaded_white.csv']

            for blob_name in files_to_process:
                try:
                    # Controlla se il file esiste
                    blob_client = container_client.get_blob_client(blob_name)
                    exists = await blob_client.exists()
                    
                    if not exists:
                        logging.info(f"File {blob_name} non trovato, skipping...")
                        continue

                    # Determina il tipo di vino dal nome del file
                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f"Processing {wine_type} wine dataset")

                    # Leggi il contenuto del blob in modo asincrono
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    
                    # Processa i dati in modo asincrono
                    df_raw = await asyncio.to_thread(
                        pd.read_csv,
                        BytesIO(content),
                        sep=";"
                    )

                    # Preprocessing con wine_type
                    df_cleaned, scaler = await asyncio.to_thread(
                        preprocess,
                        df_raw,
                        wine_type
                    )

                    # Training e salvataggio
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    
                    # Training del modello in modo asincrono
                    model_bytes, scaler_bytes = await asyncio.to_thread(
                        train_and_save_model,
                        df_cleaned,
                        scaler
                    )

                    # Usa i binding per salvare gli output
                    modelOutput.set(model_bytes)
                    scalerOutput.set(scaler_bytes)
                    cleanedOutput.set(df_cleaned.to_csv(index=False).encode())

                    logging.info(f"Training completed for {wine_type} wine")

                except Exception as e:
                    logging.error(f"Error processing {blob_name}: {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"General error in train function: {str(e)}")
        raise