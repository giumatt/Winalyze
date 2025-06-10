import azure.functions as func
import logging
import os
from azure.storage.blob import BlobServiceClient
from shared.test.train_validate import validate_model
from shared.promote import trigger_merge_to_alpha

async def main(myblob: func.InputStream) -> None:
    try:
        # Determine wine type from blob name
        blob_name = myblob.name
        wine_type = "red" if "model_red" in blob_name else "white"
        logging.info(f"Model validation started for {wine_type} wine")

        # Initialize the Azure Blob Service client
        connection_string = os.environ["AzureWebJobsStorage"]
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        # Perform model validation using helper function
        validation_result = validate_model(wine_type, blob_service)
        
        if validation_result:
            logging.info(f"Validation successful for {wine_type} wine model")

            # Define source (testing) and destination (production) containers
            test_container = blob_service.get_container_client("models-testing")
            prod_container = blob_service.get_container_client("models")
            
            # Reference to source blob (with -testing suffix)
            source_blob = test_container.get_blob_client(f"model_{wine_type}-testing.pkl")
            
            # Reference to destination blob (without -testing suffix)
            dest_blob = prod_container.get_blob_client(f"model_{wine_type}.pkl")
            
            # Copy the validated model to production container
            dest_blob.start_copy_from_url(source_blob.url)
            
            # Delete the original blob from testing container after successful copy
            source_blob.delete_blob()
                
            logging.info(f"Model for {wine_type} wine successfully moved to production and renamed")
        else:
            logging.warning(f"Validation failed for {wine_type} wine model")

    except Exception as e:
        logging.error(f"Model validation process encountered an error: {str(e)}")
        raise