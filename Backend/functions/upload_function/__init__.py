import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service = BlobServiceClient.from_connection_string(connection_string)

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        wine_type = req.params.get("type")
        if not wine_type:
            return func.HttpResponse("Missing 'type' parameter", status_code=400)

        file = req.files.get("file")
        if not file:
            return func.HttpResponse("Missing file", status_code=400)

        blob_client = blob_service.get_blob_client(container="raw", blob=file.filename)
        blob_client.upload_blob(file.stream.read(), overwrite=True, metadata={"type": wine_type})

        return func.HttpResponse(
            f"File uploaded as {file.filename} and training triggered.",
            status_code=200
        )

    except Exception as e:
        return func.HttpResponse(f"Internal Server Error: {str(e)}", status_code=500)