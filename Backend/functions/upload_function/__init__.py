import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Upload function triggered')

    wine_type = req.params.get('type')
    if not wine_type:
        return func.HttpResponse("Missing 'type' query parameter", status_code=400)
    
    if wine_type not in ['red', 'white']:
        return func.HttpResponse("Invalid wine type. It must be 'red' or 'white'", status_code=400)
    
    try:
        file = req.files.get("file")
        if not file:
            return func.HttpResponse("Missing file upload", status_code=400)
        
        blob_name = f"uploaded_{wine_type}.csv"
        blob_client = blob_service_client.get_blob_client(container="raw", blob=blob_name)

        if blob_client.exists():
            logging.warning(f"File {blob_name} already exists. I'll delete it")
            blob_client.delete_blob()

        blob_client.upload_blob(file.stream.read(), overwrite=True, metadata={"type": wine_type})

        return func.HttpResponse(f"File uploaded as {blob_name} and training triggered", status_code=200)
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return func.HttpResponse(f"Internal server error: {str(e)}", status_code=500)