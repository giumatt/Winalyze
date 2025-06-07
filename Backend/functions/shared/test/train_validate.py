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
    Valida il modello e lo sposta in production se passa i test
    
    Args:
        wine_type: Tipo di vino ('red' o 'white')
        blob_service: Client per accedere al blob storage
    
    Returns:
        bool: True se la validazione è riuscita, False altrimenti
    """
    try:
        logging.info(f"Starting validation for {wine_type} model")

        # Download model and scaler
        model_container = blob_service.get_container_client("models-testing")
        model_blob = model_container.get_blob_client(f"model_{wine_type}-testing.pkl")
        scaler_container = blob_service.get_container_client("models")
        scaler_blob = scaler_container.get_blob_client(f"scaler_{wine_type}.pkl")

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
            # Sposta il modello da testing a production
            test_container = blob_service.get_container_client("models-testing")
            prod_container = blob_service.get_container_client("models")
            
            # Get source blob
            source_blob = test_container.get_blob_client(f"model_{wine_type}-testing.pkl")
            
            # Get destination blob
            dest_blob = prod_container.get_blob_client(f"model_{wine_type}.pkl")
            
            # Copy blob
            dest_blob.start_copy_from_url(source_blob.url)
            
            # Delete source blob
            source_blob.delete_blob()
            
            logging.info(f"Modello {wine_type} promosso in production")
            return True
            
        else:
            logging.warning(f"Validation failed for {wine_type} model")
            return False

    except Exception as e:
        logging.error(f"Error validating {wine_type} model: {str(e)}")
        return False