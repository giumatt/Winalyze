import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient
from shared.model_utils import train_model
import pandas as pd
from io import BytesIO
import os
import json
import asyncio
from shared.test.train_validate import validate_model
from shared.promote import trigger_merge_to_alpha
from model_status import check_model_status

async def main(mytimer: func.TimerRequest) -> None:
    logging.info('Training function triggered by timer')

    try:
        connection_string = os.getenv("AzureWebJobsStorage")
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("cleaned")
            models_testing_container = blob_service.get_container_client("models-testing")
            models_container = blob_service.get_container_client("models")

            # Itera sui tipi di vino da processare
            for wine_type in ['red', 'white']:
                try:
                    # Carica i dati preprocessati
                    cleaned_blob = container_client.get_blob_client(f"cleaned_{wine_type}.csv")
                    if not await cleaned_blob.exists():
                        logging.warning(f"File cleaned per {wine_type} non trovato, skipping...")
                        continue

                    logging.info(f"Training {wine_type} wine model")

                    # Carica i dati preprocessati
                    blob_data = await cleaned_blob.download_blob()
                    content = await blob_data.readall()
                    df_cleaned = pd.read_csv(BytesIO(content), sep=";")

                    # Training
                    model_bytes = await asyncio.to_thread(train_model, df_cleaned, wine_type)
                    
                    # Salva il modello nel container 'models-testing'
                    model_blob = models_testing_container.get_blob_client(f"model_{wine_type}-testing.pkl")
                    await model_blob.upload_blob(model_bytes, overwrite=True)
                    
                    logging.info(f"Training completato per {wine_type}")

                    # Validazione del modello
                    try:
                        validation_result = await validate_model(wine_type, blob_service)
                        if validation_result:
                            logging.info(f"Validazione superata per il modello {wine_type}")
                        else:
                            logging.warning(f"Validazione fallita per il modello {wine_type}")
                    except Exception as e:
                        logging.error(f"Errore durante la validazione del modello {wine_type}: {str(e)}")
                    
                    # --- BLOCCO CORRETTO PER IL CHECK DELLO STATO ---
                    try:
                        logging.info(f"▶️  Esecuzione controllo status per {wine_type}")
                        await check_model_status(wine_type)
                        logging.info(f"✅ Controllo status completato per {wine_type}")
                    except Exception as e:
                        logging.error(f"Errore durante l'esecuzione di check_model_status per {wine_type}: {str(e)}")

                except Exception as e:
                    logging.error(f"Errore nel processare {wine_type}: {str(e)}")
                    continue  # Passa al prossimo tipo di vino

            # Controlla se i modelli sono pronti per la promozione
            try:
                prod_container = blob_service.get_container_client("models")
                existing_models = [b.name async for b in prod_container.list_blobs()]
                if "model_red.pkl" in existing_models and "model_white.pkl" in existing_models:
                    logging.info("🚀 Entrambi i modelli sono in produzione — trigger merge to alpha")
                    trigger_merge_to_alpha()
                else:
                    logging.info("⏳ Attesa: entrambi i modelli non sono ancora in produzione.")
            except Exception as e:
                logging.error(f"Errore nel controllo finale dei modelli in produzione: {str(e)}")

    except Exception as e:
        logging.error(f"Errore generale nella funzione di training (TimerTrigger): {str(e)}")
        raise