import pandas as pd
import joblib
import io
import os
import logging
from typing import Dict
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from azure.storage.blob import BlobServiceClient

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

def validate_model(wine_type: str, blob_service: BlobServiceClient) -> bool:
    """
    Validate model against test dataset.
    
    Args:
        wine_type: Type of wine model to validate ('red' or 'white')
        blob_service: BlobServiceClient instance
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    try:
        logging.info(f"Starting validation for {wine_type} model")

        # Download model and scaler
        model_container = blob_service.get_container_client("models")
        model_blob = model_container.get_blob_client(f"model_{wine_type}.pkl")
        scaler_blob = model_container.get_blob_client(f"scaler_{wine_type}.pkl")

        model = joblib.load(io.BytesIO(model_blob.download_blob().readall()))
        scaler = joblib.load(io.BytesIO(scaler_blob.download_blob().readall()))

        # Load test data
        test_container = blob_service.get_container_client("test-data")
        test_blob = test_container.get_blob_client(f"test_{wine_type}.csv")
        
        df = pd.read_csv(
            io.BytesIO(test_blob.download_blob().readall()),
            sep=";"
        )

        X = df.drop("quality", axis=1)
        y = df["quality"]

        # Preprocess test data
        X_scaled = scaler.transform(X)
        
        # Make predictions and evaluate
        y_pred = model.predict(X_scaled)
        metrics = get_metrics(y, y_pred)
        
        # Log metrics
        for metric_name, value in metrics.items():
            logging.info(f"{wine_type} model {metric_name}: {value:.4f}")

        # Define validation thresholds
        thresholds = {
            'accuracy': 0.70,
            'precision': 0.65,
            'recall': 0.65,
            'f1': 0.65
        }
        
        # Check if all metrics pass thresholds
        validation_passed = all(
            metrics[metric] >= threshold 
            for metric, threshold in thresholds.items()
        )

        if validation_passed:
            logging.info(f"Validation successful for {wine_type} model")
        else:
            logging.warning(f"Validation failed for {wine_type} model")
            
        return validation_passed

    except Exception as e:
        logging.error(f"Error validating {wine_type} model: {str(e)}")
        raise