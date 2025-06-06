import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_model
from validate_function.__init__ import main as validate_func
import asyncio

async def main(mytimer: func.TimerRequest,
              cleanedOutput: func.Out[bytes]) -> None:
    logging.info('Train function triggered by timer')

    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")
            models_testing_container = blob_service.get_container_client("models-testing")
            models_container = blob_service.get_container_client("models")

            files_to_process = ['uploaded_red.csv', 'uploaded_white.csv']

            for blob_name in files_to_process:
                try:
                    blob_client = container_client.get_blob_client(blob_name)
                    exists = await blob_client.exists()
                    
                    if not exists:
                        logging.info(f"File {blob_name} non trovato, skipping...")
                        continue

                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f"Processing {wine_type} wine dataset")

                    # Leggi e processa i dati
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    df_raw = await asyncio.to_thread(pd.read_csv, BytesIO(content), sep=";")
                    
                    # Train model
                    df_cleaned, scaler = await asyncio.to_thread(preprocess, df_raw, wine_type)
                    model_bytes, scaler_bytes = await asyncio.to_thread(
                        train_model, 
                        df_cleaned, 
                        scaler,
                        wine_type
                    )

                    # Salva SOLO in models-testing con il suffisso -testing
                    model_blob = models_testing_container.get_blob_client(f"model_{wine_type}-testing.pkl")
                    await model_blob.upload_blob(model_bytes, overwrite=True)

                    # Salva lo scaler in models
                    scaler_blob = models_container.get_blob_client(f"scaler_{wine_type}.pkl")
                    await scaler_blob.upload_blob(scaler_bytes, overwrite=True)

                    # Salva il dataset pulito
                    cleanedOutput.set(df_cleaned.to_csv(index=False).encode())

                    logging.info(f"Training completato per vino {wine_type}")

                    # Chiama validate_function
                    class MockBlob:
                        def __init__(self, name):
                            self.name = name
                    
                    mock_blob = MockBlob(f"models-testing/model_{wine_type}-testing.pkl")
                    await validate_func(mock_blob)

                    logging.info(f"Validazione richiesta per il modello {wine_type}")

                except Exception as e:
                    logging.error(f"Error processing {blob_name}: {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"General error in train function: {str(e)}")
        raise