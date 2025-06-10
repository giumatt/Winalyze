import logging
import os
import json
import azure.functions as func
from azure.storage.blob import BlobServiceClient

async def check_model_status(wine_type: str) -> dict:
    # Retrieve the connection string for Azure Blob Storage from environment variables
    connection_string = os.getenv("AzureWebJobsStorage")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # Get a client to access the 'models' container where trained models are stored
    container = blob_service.get_container_client("models")

    # List all blob names currently present in the 'models' container
    existing_blobs = [b.name for b in container.list_blobs()]
    
    # Determine model status based on whether the model file exists in the container
    status = "ready" if f"model_{wine_type}.pkl" in existing_blobs else "training"
    
    return {"status": status, "wine_type": wine_type}

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Initiating model status check...")

    # Extract the 'wine_type' parameter from the query string
    wine_type = req.params.get("wine_type")
    if wine_type not in ["red", "white"]:
        return func.HttpResponse(json.dumps({"error": "Invalid or missing wine_type"}), status_code=400, mimetype="application/json")

    # Try to retrieve and return the model status for the requested wine type
    try:
        result = await check_model_status(wine_type)

        logging.info(f"Model status retrieved for {wine_type}: {result}")
        
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except Exception as e:
        logging.error(f"Failed to retrieve model status: {str(e)}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")