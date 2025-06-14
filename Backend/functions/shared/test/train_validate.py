import pandas as pd
import joblib
import io
import os
from typing import Dict
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from azure.storage.blob.aio import BlobServiceClient
import logging

def get_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, float]:
    """
    Calculate model performance metrics.
    
    Args:
        y_true: Actual values
        y_pred: Predicted values
        
    Returns:
        Dictionary containing metrics
    """
    return {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted'),
        'recall': recall_score(y_true, y_pred, average='weighted'),
        'f1': f1_score(y_true, y_pred, average='weighted')
    }

async def validate_model(wine_type: str, blob_service: BlobServiceClient) -> bool:
    """
    Validates the model and promotes it to production if it passes the evaluation.
    
    Args:
        wine_type: Type of wine ('red' or 'white')
        blob_service: Client to access blob storage
    
    Returns:
        bool: True if validation succeeded, False otherwise
    """
    try:
        logging.info(f"Starting validation for {wine_type} model")

        # Download model and scaler using direct blob access
        model_blob = blob_service.get_blob_client(container="models-testing", 
                                                blob=f"model_{wine_type}-testing.pkl")
        scaler_blob = blob_service.get_blob_client(container="models", 
                                                 blob=f"scaler_{wine_type}.pkl")

        # Download and load the model
        blob_model_stream = await model_blob.download_blob()
        model_data = await blob_model_stream.readall()
        model = joblib.load(io.BytesIO(model_data))

        # Download and load the scaler
        blob_scaler_stream = await scaler_blob.download_blob()
        scaler_data = await blob_scaler_stream.readall()
        scaler = joblib.load(io.BytesIO(scaler_data))

        # Load test data
        test_blob = blob_service.get_blob_client(container="test-data", 
                                               blob=f"test_{wine_type}.csv")
        
        test_stream = await test_blob.download_blob()
        test_data = await test_stream.readall()
        df = pd.read_csv(io.BytesIO(test_data), sep=";")

        X = df.drop("quality", axis=1)
        y = df["quality"]

        # Preprocess test data by scaling features
        X_scaled = scaler.fit_transform(X)
        
        # Make predictions and evaluate
        y_pred = model.predict(X_scaled)
        metrics = get_metrics(y, y_pred)
        
        # Log metrics
        for metric_name, value in metrics.items():
            logging.info(f"{wine_type} model {metric_name}: {value:.4f}")

        # Define performance thresholds for validation
        thresholds = {
            'accuracy': 0.70,
            'precision': 0.60,
            'recall': 0.70,
            'f1': 0.65
        }
        
        validation_passed = all(
            metrics[metric] >= threshold 
            for metric, threshold in thresholds.items()
        )

        if validation_passed:
            logging.info(f"Validation successful for {wine_type} model")
            
            # Promote the model to production
            prod_blob = blob_service.get_blob_client(container="models", 
                                                   blob=f"model_{wine_type}.pkl")
            
            # Direct upload to production
            await prod_blob.upload_blob(model_data, overwrite=True)
            
            # Delete the testing version
            await model_blob.delete_blob()
            
            logging.info(f"Model {wine_type} promoted to production")
            return True
            
        logging.warning(f"Validation failed for {wine_type} model")
        return False

    except Exception as e:
        logging.error(f"Error validating {wine_type} model: {str(e)}")
        return False