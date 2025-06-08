import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.model_utils import preprocess_data
import asyncio

async def main(blob: func.InputStream):
    logging.info('Blob trigger function initiated')
    
    try:
        connection_string = os.getenv("AzureWebJobsStorage")
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")
            cleaned_container = blob_service.get_container_client("cleaned")
            
            for blob_name in ['uploaded_red.csv', 'uploaded_white.csv']:
                try:
                    blob_client = blob.get_blob_client(blob_name)
                    if not await blob_client.exists():
                        logging.info(f"File {blob_name} non trovato, skipping...")
                        continue

                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f'Processing {wine_type} wine dataset from blob {blob_name}')
                
                    # Carica i dati dal blob
                    blob_data = await blob.read()
                    df_raw = await asyncio.to_thread(pd.read_csv, BytesIO(blob_data), sep=";")
                
                    # Preprocessing
                    df_cleaned, scaler_bytes = await asyncio.to_thread(
                        preprocess_data,
                        df_raw,
                        wine_type
                    )
                
                    # Salva i dati preprocessati nel container 'cleaned'
                    cleaned_blob = cleaned_container.get_blob_client(f"cleaned_{wine_type}.csv")
                    await cleaned_blob.upload_blob(
                        df_cleaned.to_csv(index=False).encode(),
                        overwrite=True
                    )

                    # Salva lo scaler
                    scaler_blob = cleaned_container.get_blob_client(f"scaler_{wine_type}.pkl")
                    await scaler_blob.upload_blob(scaler_bytes, overwrite=True)
                
                    logging.info(f'Data preprocessing completed for {wine_type}')

                     # Verifica che il blob esista prima di procedere
                    if not await cleaned_blob.exists():
                        logging.error(f"Errore: il file cleaned per {wine_type} non è stato salvato correttamente")
                        continue
                except Exception as e:
                    logging.error(f'Error during preprocessing: {str(e)}')
    except Exception as e:
        logging.error(f'Error during preprocessing: {str(e)}')
        raise