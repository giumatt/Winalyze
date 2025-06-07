import logging
import os
import json
import asyncio
import azure.functions as func
from azure.storage.blob import BlobServiceClient

async def check_model_status(wine_type: str) -> dict:
    connection_string = os.getenv("AzureWebJobsStorage")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container = blob_service.get_container_client("models")

    existing_blobs = [b.name async for b in container.list_blobs()]
    status = "ready" if f"model_{wine_type}.pkl" in existing_blobs else "training"
    return {wine_type: status}

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("🔍 Model status check initiated")

    wine_type = req.params.get("wine_type")
    if wine_type not in ["red", "white"]:
        return func.HttpResponse(json.dumps({"error": "Invalid or missing wine_type"}), status_code=400, mimetype="application/json")

    try:
        result = await check_model_status(wine_type)
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")