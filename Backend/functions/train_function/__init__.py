import azure.functions as func
import logging
import os
import pandas as pd
from io import BytesIO
from azure.storage.blob import BlobClient
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_and_save_model
from datetime import datetime, timezone

def main(inputblob: func.InputStream, name: str):
    logging.info(f"Function triggered for blob: {inputblob.name}")
    logging.info(f"Blob size: {inputblob.length} bytes")
    
    try:
        filename = name.lower().strip()
        if "red" in filename:
            wine_type = "red"
        elif "white" in filename:
            wine_type = "white"
        else:
            logging.warning("Wine type not recognized")
        
        logging.info(f"Wine type detected: {wine_type}")
        logging.info(f"Starting preprocessing for {wine_type} wine")
        
        df_raw = pd.read_csv(BytesIO(inputblob), sep=";")
        logging.info(f"[TRAIN] Loaded raw data: {df_raw.shape}")

        # Preprocessing
        df_cleaned, scaler = preprocess(df_raw)
        logging.info(f"[TRAIN] Cleaned data: {df_cleaned.shape}")

        # Serialize cleaned CSV
        cleaned_buffer = BytesIO()
        df_cleaned.to_csv(cleaned_buffer, index=False)
        cleaned_buffer.seek(0)

        # Train and serialize model
        model_bytes, scaler_bytes = train_and_save_model(df_cleaned, scaler)
        logging.info("[TRAIN] Model and scaler serialized")

        # Timestamp versioning
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

        # Blob Storage upload
        conn_str = os.environ["AzureWebJobsStorage"]
        output_files = {
            f"cleaned/{wine_type}/preprocessed_{timestamp}.csv": cleaned_buffer.getvalue(),
            f"models/{wine_type}/model_{timestamp}.pkl": model_bytes,
            f"models/{wine_type}/scaler_{timestamp}.pkl": scaler_bytes,
        }

        for path, content in output_files.items():
            container, *blob_parts = path.split('/')
            blob_path = '/'.join(blob_parts)
            blob = BlobClient.from_connection_string(
                conn_str, container_name=container, blob_name=blob_path
            )
            blob.upload_blob(content, overwrite=True)
            logging.info(f"[TRAIN] Uploaded to: {path}")

        logging.info("Training and save completed")
    except Exception as e:
        logging.error(f"Error in training function: {str(e)}")
        logging.exception("Full stack trace:")
        raise