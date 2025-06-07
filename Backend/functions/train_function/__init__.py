import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.model_utils import preprocess_data, train_model
from shared.test.train_validate import validate_model
import asyncio

async def main(mytimer: func.TimerRequest,
              cleanedOutput: func.Out[bytes]) -> None:
    logging.info('Train function triggered by timer')

    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")
            cleaned_container = blob_service.get_container_client("cleaned")
            models_testing_container = blob_service.get_container_client("models-testing")
            models_container = blob_service.get_container_client("models")

            for blob_name in ['uploaded_red.csv', 'uploaded_white.csv']:
                try:
                    # Carica dati raw
                    blob_client = container_client.get_blob_client(blob_name)
                    if not await blob_client.exists():
                        logging.info(f"File {blob_name} non trovato, skipping...")
                        continue

                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f"Processing {wine_type} wine dataset")

                    # Carica e preprocessa i dati raw
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    df_raw = await asyncio.to_thread(pd.read_csv, BytesIO(content), sep=";")
                    
                    # Preprocessing e salvataggio in cleaned
                    df_cleaned, scaler_bytes = await asyncio.to_thread(
                        preprocess_data,
                        df_raw,
                        wine_type
                    )
                    
                    # Salva direttamente nel container cleaned invece di usare il binding
                    cleaned_blob = cleaned_container.get_blob_client(f"cleaned_{wine_type}.csv")
                    await cleaned_blob.upload_blob(
                        df_cleaned.to_csv(index=False).encode(),
                        overwrite=True
                    )

                    # Salva lo scaler
                    scaler_blob = models_container.get_blob_client(f"scaler_{wine_type}.pkl")
                    await scaler_blob.upload_blob(scaler_bytes, overwrite=True)
                    
                    logging.info(f"Dati preprocessati e scaler salvati per {wine_type}")

                    # Aggiungi una breve attesa per essere sicuri che il blob sia disponibile
                    await asyncio.sleep(1)

                    # Verifica che il blob esista prima di procedere
                    if not await cleaned_blob.exists():
                        logging.error(f"Errore: il file cleaned per {wine_type} non è stato salvato correttamente")
                        continue

                    # Carica i dati da cleaned per il training
                    cleaned_data = await cleaned_blob.download_blob()
                    cleaned_content = await cleaned_data.readall()
                    df_for_training = await asyncio.to_thread(
                        pd.read_csv,
                        BytesIO(cleaned_content)
                    )
                    
                    # Training usando i dati da cleaned
                    model_bytes = await asyncio.to_thread(
                        train_model,
                        df_for_training,
                        wine_type
                    )

                    # Salva il modello in testing
                    model_blob = models_testing_container.get_blob_client(f"model_{wine_type}-testing.pkl")
                    await model_blob.upload_blob(model_bytes, overwrite=True)
                    
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