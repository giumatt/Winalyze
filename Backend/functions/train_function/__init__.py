import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_and_save_model
import asyncio

async def main(mytimer: func.TimerRequest,
              modelTestOutput: func.Out[bytes],
              scalerOutput: func.Out[bytes],
              cleanedOutput: func.Out[bytes]) -> None:
    logging.info('Train function triggered by timer')

    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")

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
                    
                    # Preprocessing e training
                    df_cleaned, scaler = await asyncio.to_thread(preprocess, df_raw, wine_type)
                    model_bytes, scaler_bytes = await asyncio.to_thread(
                        train_and_save_model, 
                        df_cleaned, 
                        scaler,
                        wine_type
                    )

                    # Salva il modello con suffisso -testing in models-test e lo scaler direttamente in models
                    modelTestOutput.set(model_bytes)  # Sarà model_{wine_type}-testing.pkl in models-test
                    scalerOutput.set(scaler_bytes)    # Sarà scaler_{wine_type}.pkl in models
                    cleanedOutput.set(df_cleaned.to_csv(index=False).encode())

                    logging.info(f"Training completato per vino {wine_type}:")
                    logging.info(f"- Modello salvato come model_{wine_type}-testing.pkl in models-test")
                    logging.info(f"- Scaler salvato come scaler_{wine_type}.pkl in models")

                except Exception as e:
                    logging.error(f"Error processing {blob_name}: {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"General error in train function: {str(e)}")
        raise