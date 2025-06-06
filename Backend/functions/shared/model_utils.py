import joblib
import io
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from azure.storage.blob import BlobServiceClient
import os
import logging
from typing import Tuple, Any
from sklearn.preprocessing import StandardScaler
import pickle

def train_model(df: pd.DataFrame, scaler: StandardScaler, wine_type: str) -> Tuple[bytes, bytes]:
    """
    Train model and return serialized model and scaler
    """
    # Separa features e target
    X = df.drop('quality', axis=1)
    y = df['quality']
    
    # Scala i dati
    X_scaled = scaler.transform(X)
    
    # Addestra il modello
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    
    # Serializza modello e scaler
    model_bytes = pickle.dumps(model)
    scaler_bytes = pickle.dumps(scaler)
    
    return model_bytes, scaler_bytes

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