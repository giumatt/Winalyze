import azure.functions as func
import logging
import os
import io
from azure.storage.blob import BlobServiceClient
from test.train_validate import validate_model
from shared.promote import promote_to_alpha

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service = BlobServiceClient.from_connection_string(connection_string)

def main(myblob: func.InputStream):
    blob_name = myblob.name  # es: models/model_red.pkl
    logging.info(f"🧪 Triggered by new blob: {blob_name}")

    try:
        if 'model_red.pkl' in blob_name:
            wine_type = "red"
        elif 'model_white.pkl' in blob_name:
            wine_type = "white"
        else:
            logging.warning("Blob not recognized. No validation done")
            return

        validate_model(wine_type)
        logging.info(f"Model '{wine_type}' validated successfully.")

        # 🔁 Promozione GitHub
        promote_to_alpha()

    except Exception as e:
        logging.error(f"Error while model validation: {e}")
        raise