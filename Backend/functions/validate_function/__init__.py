import azure.functions as func
import logging
import os
from azure.storage.blob import BlobServiceClient
from test.train_validate import validate_model
from shared.promote import promote_to_alpha

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function that runs every hour to validate models and promote to alpha if validation passes.
    """
    logging.info('Validation timer trigger function started')

    try:
        # Initialize blob service
        connection_string = os.environ["AzureWebJobsStorage"]
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        # Process both wine types
        for wine_type in ["red", "white"]:
            try:
                # Check if model exists
                model_container = blob_service.get_container_client("models")
                model_blob = model_container.get_blob_client(f"model_{wine_type}.pkl")
                
                if not model_blob.exists():
                    logging.info(f"No model found for {wine_type} wine")
                    continue

                # Validate model
                validation_result = validate_model(wine_type, blob_service)
                
                if validation_result:
                    logging.info(f"Model validation successful for {wine_type} wine")
                    
                    # Promote to alpha branch
                    promote_to_alpha(wine_type)
                    logging.info(f"Model promoted to alpha branch for {wine_type} wine")
                else:
                    logging.warning(f"Model validation failed for {wine_type} wine")

            except Exception as e:
                logging.error(f"Error processing {wine_type} wine: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Validation process failed: {str(e)}")
        raise