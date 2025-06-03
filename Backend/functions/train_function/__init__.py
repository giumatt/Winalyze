import azure.functions as func
import logging
import os
import pandas as pd
import io
import joblib
from azure.storage.blob import BlobServiceClient
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_and_save_model

def main(inputblob: func.InputStream):
    try:
        logging.info(f"Trigger received: {inputblob.name}")

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        filename = inputblob.name
        if "red" in filename:
            wine_type = "red"
        elif "white" in filename:
            wine_type = "white"
        else:
            logging.warning("Wine type not recognized")
            return
        
        csv_bytes = inputblob.read()
        df = pd.read_csv(io.BytesIO(csv_bytes))

        df_cleaned, scaler = preprocess(df)
        cleaned_path = f"cleaned/cleaned_{wine_type}.csv"
        blob_service.get_blob_client(container="cleaned", blob=cleaned_path)\
                    .upload_blob(io.BytesIO(df_cleaned.to_csv(index=False).encode()), overwrite=True)
        
        model_bytes, scaler_bytes = train_and_save_model(df_cleaned, scaler)

        blob_service.get_blob_client(container="models", blob=f"model_{wine_type}.pkl")\
                    .upload_blob(io.BytesIO(model_bytes), overwrite=True)
        blob_service.get_blob_client(container="models", blob=f"scaler_{wine_type}.pkl")\
                    .upload_blob(io.BytesIO(scaler_bytes), overwrite=True)
        
        logging.info("Training and save completed")
    except Exception as e:
        logging.error(f"Error while training model: {e}")
        