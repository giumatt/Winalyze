import joblib
import os
import io
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

blob_service = BlobServiceClient.from_connection_string(connection_string)
testing_blob = blob_service.get_blob_client(container="models", blob="model_testing.pkl")
testing_model_bytes = testing_blob.download_blob().readall()

prod_blob = blob_service.get_blob_client(container="models", blob="model_production.pkl")
prod_blob.upload_blob(testing_model_bytes, overwrite=True)

print("Model promoted to production")