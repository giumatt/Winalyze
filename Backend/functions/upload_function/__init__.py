import logging
import azure.functions as func
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
import os
import pandas as pd
import io
import json
import asyncio

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Upload function triggered')

    try:
        # Get file from request
        file = req.files.get('file')
        if not file:
            return func.HttpResponse("Missing file in request", status_code=400)
        
        # Read file content asynchronously
        file_content = await asyncio.to_thread(file.stream.read)
        original_filename = file.filename or ""
        original_filename = original_filename.lower().strip()

        # Determine wine type from filename
        if "red" in original_filename:
            wine_type = "red"
        elif "white" in original_filename:
            wine_type = "white"
        else:
            return func.HttpResponse("Filename must contain 'red' or 'white'", status_code=400)
        
        # Generate blob name
        blob_name = f"uploaded_{wine_type}.csv"

        # Initialize async blob service client
        async with BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        ) as blob_service_client:
            # Get container client
            container_client = blob_service_client.get_container_client("raw")
            
            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)

            try:
                # Upload file asynchronously
                await blob_client.upload_blob(
                    file_content,
                    overwrite=True,
                    content_settings={
                        "content_type": "text/csv",
                        "content_encoding": "utf-8"
                    }
                )

                # Generate preview asynchronously
                df = await asyncio.to_thread(
                    pd.read_csv,
                    io.BytesIO(file_content),
                    sep=";",
                    nrows=5
                )
                preview_data = await asyncio.to_thread(
                    df.to_dict,
                    orient='records'
                )

                response_data = {
                    "message": f"File uploaded as: {blob_name}",
                    "preview": preview_data
                }

                logging.info(f"Successfully uploaded blob: {blob_name}")
                return func.HttpResponse(
                    json.dumps(response_data),
                    mimetype="application/json",
                    status_code=200
                )

            except ResourceExistsError:
                return func.HttpResponse(
                    f"A blob with name {blob_name} already exists",
                    status_code=409
                )
            
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        logging.exception("Full stack trace:")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)