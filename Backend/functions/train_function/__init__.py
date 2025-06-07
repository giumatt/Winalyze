import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.model_utils import train_model
from shared.test.train_validate import validate_model
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

            # Verifica se il container raw ha file da processare
            blobs = [blob async for blob in container_client.list_blobs()]
            if not blobs:
                logging.info("Nessun file da processare nel container raw")
                return

            for blob_name in ['uploaded_red.csv', 'uploaded_white.csv']:
                try:
                    # Carica dati raw
                    blob_client = container_client.get_blob_client(blob_name)
                    if not await blob_client.exists():
                        logging.info(f"File {blob_name} non trovato, skipping...")
                        continue

                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f"Processing {wine_type} wine dataset")

                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    df_raw = await asyncio.to_thread(pd.read_csv, BytesIO(content), sep=";")
                    
                    # Training unificato
                    model_bytes, scaler_bytes = await asyncio.to_thread(
                        train_model, 
                        df_raw,
                        wine_type
                    )

                    # Salva gli artefatti
                    model_blob = models_testing_container.get_blob_client(f"model_{wine_type}-testing.pkl")
                    await model_blob.upload_blob(model_bytes, overwrite=True)

                    scaler_blob = models_container.get_blob_client(f"scaler_{wine_type}.pkl")
                    await scaler_blob.upload_blob(scaler_bytes, overwrite=True)

                    logging.info(f"Training completato per vino {wine_type}")

                    try:
                        # Verifica se ci sono modelli da validare in models-testing
                        testing_blobs = [blob async for blob in models_testing_container.list_blobs()]
                        if not testing_blobs:
                            logging.info("Nessun modello da validare in models-testing")
                            continue

                        # Verifica se esiste il modello specifico da validare
                        model_test_name = f"model_{wine_type}-testing.pkl"
                        if not any(blob.name == model_test_name for blob in testing_blobs):
                            logging.info(f"Modello {model_test_name} non trovato in models-testing")
                            continue

                        # Valida il modello
                        validation_result = await validate_model(wine_type, blob_service)
                        if validation_result:
                            logging.info(f"Validazione superata per il modello {wine_type}")
                        else:
                            logging.warning(f"Validazione fallita per il modello {wine_type}")
                    except Exception as e:
                        logging.error(f"Errore durante la validazione del modello {wine_type}: {str(e)}")

                except Exception as e:
                    logging.error(f"Error processing {blob_name}: {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"General error in train function: {str(e)}")
        raise