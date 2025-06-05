import joblib
import io
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from azure.storage.blob import BlobServiceClient
import os
import logging
from typing import Tuple, Any

def train_and_save_model(df_cleaned: pd.DataFrame, scaler: Any, wine_type: str) -> Tuple[bytes, bytes]:
    """
    Addestra e salva il modello per un tipo specifico di vino.
    
    Args:
        df_cleaned (pd.DataFrame): DataFrame preprocessato
        scaler: Scaler addestrato sui dati
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        Tuple[bytes, bytes]: Coppia di (model_bytes, scaler_bytes)
    """
    try:
        if wine_type not in ['red', 'white']:
            raise ValueError("wine_type deve essere 'red' o 'white'")

        X = df_cleaned.drop("quality", axis=1)
        y = df_cleaned["quality"]
        
        model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced'
        )
        model.fit(X, y)

        # Serializzazione
        model_bytes = io.BytesIO()
        scaler_bytes = io.BytesIO()
        
        joblib.dump(model, model_bytes)
        joblib.dump(scaler, scaler_bytes)
        
        model_bytes.seek(0)
        scaler_bytes.seek(0)

        connection_string = os.getenv("AzureWebJobsStorage")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("models")

        model_blob = container_client.get_blob_client(f"model_{wine_type}.pkl")
        model_blob.upload_blob(model_bytes.getvalue(), overwrite=True)

        scaler_blob = container_client.get_blob_client(f"scaler_{wine_type}.pkl")
        scaler_blob.upload_blob(scaler_bytes.getvalue(), overwrite=True)

        logging.info(f"Modello e scaler salvati con successo per vino {wine_type}")
        return model_bytes.getvalue(), scaler_bytes.getvalue()

    except Exception as e:
        logging.error(f"Errore nel salvataggio del modello: {str(e)}")
        raise

def load_model(wine_type: str):
    try:
        connection_string = os.getenv("AzureWebJobsStorage")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("models")

        model_blob = container_client.get_blob_client(f"model_{wine_type}.pkl")
        model_bytes = model_blob.download_blob().readall()

        scaler_blob = container_client.get_blob_client(f"scaler_{wine_type}.pkl")
        scaler_bytes = scaler_blob.download_blob().readall()

        model = joblib.load(io.BytesIO(model_bytes))
        scaler = joblib.load(io.BytesIO(scaler_bytes))

        logging.info(f"Modello e scaler caricati con successo per vino {wine_type}")
        return model, scaler

    except Exception as e:
        logging.error(f"Errore nel caricamento del modello: {str(e)}")
        raise