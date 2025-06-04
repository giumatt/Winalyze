import logging
import azure.functions as func
from azure.storage.blob import BlobClient
from datetime import datetime, timezone
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Upload function triggered')

    try:
        file = req.files.get('file')
        if not file:
            return func.HttpResponse("Missing file in request", status_code=400)
        
        file_content = file.stream.read()
        original_filename = file.filename or ""
        original_filename = original_filename.lower().strip()

        if "red" in original_filename:
            wine_type = "red"
        elif "white" in original_filename:
            wine_type = "white"
        else:
            return func.HttpResponse("Filename must contain red or white", status_code=400)
        
        # FIX: Corretto il formato timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        blob_name = f"uploaded_{wine_type}_{timestamp}.csv"

        blob = BlobClient.from_connection_string(
            conn_str=os.environ["AzureWebJobsStorage"],
            container_name="raw",
            blob_name=blob_name
        )
        blob.upload_blob(file_content, overwrite=True)

        logging.info(f"Successfully uploaded blob: {blob_name}")
        return func.HttpResponse(f"File uploaded as: {blob_name}", status_code=200)
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        logging.exception("Full stack trace:")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)