import joblib
import io
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from sklearn.preprocessing import StandardScaler
import pickle
import logging
from typing import Tuple
import os
from azure.storage.blob import BlobServiceClient

def train_model(df: pd.DataFrame, wine_type: str) -> Tuple[bytes, bytes]:
    """
    Preprocessa i dati, addestra il modello e restituisce modello e scaler serializzati
    
    Args:
        df (pd.DataFrame): DataFrame raw con i dati del vino
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        Tuple[bytes, bytes]: (modello serializzato, scaler serializzato)
    """
    logging.info(f"Inizio preprocessing e training per vino {wine_type}")
    
    # Preprocessing
    df_cleaned = df.copy()
    df_cleaned.dropna(inplace=True)
    
    # Separazione features e target
    X = df_cleaned.drop('quality', axis=1)
    y = df_cleaned['quality']
    
    # Standardizzazione
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Training
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_scaled, y)
    
    # Serializzazione
    model_bytes = pickle.dumps(model)
    scaler_bytes = pickle.dumps(scaler)
    
    logging.info(f"Training completato per vino {wine_type}")
    return model_bytes, scaler_bytes

def load_model(wine_type: str) -> Tuple[RandomForestClassifier, StandardScaler]:
    """
    Carica il modello e lo scaler dal blob storage
    
    Args:
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        Tuple[RandomForestClassifier, StandardScaler]: (modello, scaler)
    """
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