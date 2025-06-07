import azure.functions as func
import logging
import os
from azure.storage.blob import BlobServiceClient
from shared.test.train_validate import validate_model
from shared.promote import trigger_merge_to_alpha

async def main(myblob: func.InputStream) -> None:
    """
    Azure Function triggered when a new model is saved in models-test container.
    Validates the model and if successful, moves it to production container.
    """
    try:
        # Get wine type from blob name
        blob_name = myblob.name
        wine_type = "red" if "model_red" in blob_name else "white"
        logging.info(f"Validation triggered for {wine_type} wine model")

        # Initialize blob service
        connection_string = os.environ["AzureWebJobsStorage"]
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        # Validate model
        validation_result = validate_model(wine_type, blob_service)
        
        if validation_result:
            logging.info(f"Model validation successful for {wine_type} wine")
            
            # Move model from test to production with new name
            test_container = blob_service.get_container_client("models-testing")
            prod_container = blob_service.get_container_client("models")
            
            # Get source blob (with -testing suffix)
            source_blob = test_container.get_blob_client(f"model_{wine_type}-testing.pkl")
            
            # Get destination blob (without -testing suffix)
            dest_blob = prod_container.get_blob_client(f"model_{wine_type}.pkl")
            
            # Copy blob
            dest_blob.start_copy_from_url(source_blob.url)
            
            # Delete source blob after successful copy
            source_blob.delete_blob()
                
            logging.info(f"Model moved to production and renamed for {wine_type} wine")
            try:
                existing_models = [b.name for b in prod_container.list_blobs()]
                if "model_red.pkl" in existing_models and "model_white.pkl" in existing_models:
                    logging.info("🚀 Both models in production. Triggering promotion to alpha.")
                    trigger_merge_to_alpha()
                else:
                    logging.info("ℹ️ Not all models are present in production. Skipping promotion.")
            except Exception as e:
                logging.error(f"Failed to trigger merge to alpha: {str(e)}")
        else:
            logging.warning(f"Model validation failed for {wine_type} wine")

    except Exception as e:
        logging.error(f"Validation process failed: {str(e)}")
        raise