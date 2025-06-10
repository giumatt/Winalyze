import azure.functions as func
import logging
from azure.storage.blob.aio import BlobServiceClient
import os
import pandas as pd
from io import BytesIO
from shared.model_utils import preprocess_data, train_model
from shared.test.train_validate import validate_model
from shared.promote import trigger_merge_to_alpha
import asyncio

async def main(mytimer: func.TimerRequest,
              cleanedOutput: func.Out[bytes]) -> None:
    logging.info('Train function triggered by timer')

    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service:
            container_client = blob_service.get_container_client("raw")
            cleaned_container = blob_service.get_container_client("cleaned")
            models_testing_container = blob_service.get_container_client("models-testing")
            models_container = blob_service.get_container_client("models")

            # Iterate over the datasets of the two wine types to perform training and validation
            for blob_name in ['uploaded_red.csv', 'uploaded_white.csv']:
                try:
                    # Load and preprocess raw data
                    blob_client = container_client.get_blob_client(blob_name)
                    if not await blob_client.exists():
                        logging.info(f"File {blob_name} not found, skipping...")
                        continue

                    wine_type = 'red' if 'red' in blob_name else 'white'
                    logging.info(f"Processing {wine_type} wine dataset")

                    # Load and preprocess raw data
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    df_raw = await asyncio.to_thread(pd.read_csv, BytesIO(content), sep=";")
                    
                    # Preprocessing and saving to 'cleaned' blob
                    df_cleaned, scaler_bytes = await asyncio.to_thread(
                        preprocess_data,
                        df_raw,
                        wine_type
                    )
                    
                    # Save directly to the 'cleaned' blob instead of using the binding
                    cleaned_blob = cleaned_container.get_blob_client(f"cleaned_{wine_type}.csv")
                    await cleaned_blob.upload_blob(
                        df_cleaned.to_csv(index=False).encode(),
                        overwrite=True
                    )

                    # Save the scaler which is needed to normalize data during inference
                    scaler_blob = models_container.get_blob_client(f"scaler_{wine_type}.pkl")
                    await scaler_blob.upload_blob(scaler_bytes, overwrite=True)
                    
                    logging.info(f"Data preprocessed and scaler saved for {wine_type} wine")

                    # Add a short wait to ensure the blob is available
                    await asyncio.sleep(1)

                    # Check that the blob exists before proceeding
                    if not await cleaned_blob.exists():
                        logging.error(f"Error: the cleaned file for {wine_type} was not saved correctly")
                        continue

                    # Load data from 'cleaned' for training
                    cleaned_data = await cleaned_blob.download_blob()
                    cleaned_content = await cleaned_data.readall()
                    df_for_training = await asyncio.to_thread(
                        pd.read_csv,
                        BytesIO(cleaned_content)
                    )
                    
                    # Training using cleaned data
                    model_bytes = await asyncio.to_thread(
                        train_model,
                        df_for_training,
                        wine_type
                    )

                    # Save the model in testing
                    model_blob = models_testing_container.get_blob_client(f"model_{wine_type}-testing.pkl")
                    await model_blob.upload_blob(model_bytes, overwrite=True)
                    
                    logging.info(f"Training completed for {wine_type} wine")

                    # Validate the model and promote it if it meets criteria
                    try:
                        # Check if there are models to validate in models-testing
                        testing_blobs = [blob async for blob in models_testing_container.list_blobs()]
                        if not testing_blobs:
                            logging.info("No model to validate in models-testing")
                            continue

                        # Check if the specific model to validate exists
                        model_test_name = f"model_{wine_type}-testing.pkl"
                        if not any(blob.name == model_test_name for blob in testing_blobs):
                            logging.info(f"Model {model_test_name} not found in models-testing")
                            continue

                        # Validate the model
                        validation_result = await validate_model(wine_type, blob_service)
                        if validation_result:
                            logging.info(f"Validation passed for {wine_type} red")
                        else:
                            logging.warning(f"Validation failed for {wine_type} wine model")
                    except Exception as e:
                        logging.error(f"Error while validating {wine_type} wine model: {str(e)}")
                    
                except Exception as e:
                    logging.error(f"Error processing {blob_name}: {str(e)}")
                    continue

            # Merge to alpha branch is performed only if both models are in production
            try:
                prod_container = blob_service.get_container_client("models")
                existing_models = [b.name async for b in prod_container.list_blobs()]
                if "model_red.pkl" in existing_models and "model_white.pkl" in existing_models:
                    logging.info("Both models in prodoction — trigger merge to alpha")
                    trigger_merge_to_alpha()
                else:
                    logging.info("Waiting: not both models are in production")
            except Exception as e:
                logging.error(f"Error while checking models in production: {str(e)}")
    except Exception as e:
        logging.error(f"General error in train function: {str(e)}")
        raise